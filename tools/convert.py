#!/usr/bin/env python3
"""Convert Adblock Plus filter lists (EasyList syntax) to Chrome MV3
declarativeNetRequest static rule JSON.

Usage:
    python3 tools/convert.py easylist.txt rules_easylist.json
    python3 tools/convert.py easyprivacy.txt rules_easyprivacy.json

Only network rules are converted. Cosmetic (element-hiding) rules, regex
rules and rules using options that declarativeNetRequest cannot express
(csp, redirect, removeparam, popup, ...) are skipped and counted.
"""

import json
import re
import sys

RESOURCE_TYPE_MAP = {
    "script": "script",
    "image": "image",
    "img": "image",
    "stylesheet": "stylesheet",
    "css": "stylesheet",
    "object": "object",
    "xmlhttprequest": "xmlhttprequest",
    "xhr": "xmlhttprequest",
    "subdocument": "sub_frame",
    "frame": "sub_frame",
    "document": "main_frame",
    "doc": "main_frame",
    "ping": "ping",
    "beacon": "ping",
    "media": "media",
    "font": "font",
    "websocket": "websocket",
    "other": "other",
}

ALL_RESOURCE_TYPES = [
    "main_frame", "sub_frame", "stylesheet", "script", "image", "font",
    "object", "xmlhttprequest", "ping", "media", "websocket", "other",
]

# Options that change matching semantics in ways DNR cannot express.
# A rule carrying any of these is dropped.
UNSUPPORTED_OPTIONS = {
    "popup", "csp", "rewrite", "replace", "removeparam", "cookie",
    "header", "genericblock", "webrtc", "object-subrequest", "badfilter",
    "popunder", "app", "network", "permissions", "urltransform", "jsonprune",
}

# Options that only affect cosmetic filtering; ignore them on allow rules,
# but if they are the rule's sole purpose, drop the rule.
COSMETIC_ONLY_OPTIONS = {"generichide", "elemhide", "specifichide", "ehide", "ghide", "shide"}

DOMAIN_RULE_RE = re.compile(r"^\|\|([a-z0-9][a-z0-9.-]*[a-z0-9])\^$")
BATCH_SIZE = 2000


def is_ascii(s):
    try:
        s.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def to_ascii_domain(domain):
    """Lowercase and punycode a domain; return None if impossible."""
    domain = domain.lower()
    if is_ascii(domain):
        return domain
    try:
        return domain.encode("idna").decode("ascii")
    except (UnicodeError, UnicodeDecodeError):
        return None


def parse_options(option_str):
    """Parse the $option part. Returns (condition_extras, priority, drop_reason)."""
    cond = {}
    priority = 1
    include_types = []
    exclude_types = []
    cosmetic_only = True

    for raw in option_str.split(","):
        opt = raw.strip()
        if not opt:
            continue
        negated = opt.startswith("~")
        name, _, value = opt.lstrip("~").partition("=")
        name = name.lower()

        if name in UNSUPPORTED_OPTIONS:
            return None, None, "unsupported-option"
        if name in COSMETIC_ONLY_OPTIONS:
            continue
        cosmetic_only = False

        if name in ("third-party", "3p"):
            cond["domainType"] = "firstParty" if negated else "thirdParty"
        elif name in ("first-party", "1p"):
            cond["domainType"] = "thirdParty" if negated else "firstParty"
        elif name == "match-case":
            cond["isUrlFilterCaseSensitive"] = True
        elif name == "important":
            priority = 2
        elif name == "all":
            include_types = list(ALL_RESOURCE_TYPES)
        elif name in ("domain", "from"):
            inc, exc = [], []
            for d in value.split("|"):
                d = d.strip()
                neg = d.startswith("~")
                d = d.lstrip("~")
                if not d or "*" in d:
                    continue
                d = to_ascii_domain(d)
                if d is None:
                    continue
                (exc if neg else inc).append(d)
            if inc:
                cond["initiatorDomains"] = inc
            if exc:
                cond["excludedInitiatorDomains"] = exc
            if not inc and not exc:
                return None, None, "empty-domain-option"
        elif name in ("to",):
            inc = []
            for d in value.split("|"):
                d = to_ascii_domain(d.strip().lstrip("~"))
                if d:
                    inc.append(d)
            if inc:
                cond["requestDomains"] = inc
        elif name in ("denyallow",):
            exc = []
            for d in value.split("|"):
                d = to_ascii_domain(d.strip())
                if d:
                    exc.append(d)
            if exc:
                cond["excludedRequestDomains"] = exc
        elif name in RESOURCE_TYPE_MAP:
            (exclude_types if negated else include_types).append(RESOURCE_TYPE_MAP[name])
        else:
            return None, None, "unknown-option"

    if include_types:
        cond["resourceTypes"] = sorted(set(include_types))
    elif exclude_types:
        cond["excludedResourceTypes"] = sorted(set(exclude_types))

    return cond, priority, ("cosmetic-only" if cosmetic_only and option_str else None)


def convert(lines):
    rules = []
    plain_block_domains = []       # ||domain^            -> batched
    plain_3p_block_domains = []    # ||domain^$third-party -> batched
    stats = {"converted": 0, "cosmetic": 0, "comment": 0, "regex": 0,
             "unsupported": 0, "non-ascii": 0, "invalid": 0}
    next_id = 1

    def alloc_id():
        nonlocal next_id
        i = next_id
        next_id += 1
        return i

    for line in lines:
        line = line.strip()
        if not line or line.startswith("!") or line.startswith("["):
            stats["comment"] += 1
            continue
        if re.search(r"#[@?$]?#|##\^", line):
            stats["cosmetic"] += 1
            continue

        is_exception = line.startswith("@@")
        pattern = line[2:] if is_exception else line

        option_str = ""
        # The option separator is the last '$' not inside a regex literal.
        if "$" in pattern and not (pattern.startswith("/") and pattern.endswith("/")):
            pattern, _, option_str = pattern.rpartition("$")

        if pattern.startswith("/") and pattern.endswith("/") and len(pattern) > 2:
            stats["regex"] += 1
            continue
        if not pattern:
            stats["invalid"] += 1
            continue
        if not is_ascii(pattern):
            # Try to punycode a plain domain pattern, otherwise skip.
            m = re.match(r"^\|\|(.+?)(\^.*)$", pattern)
            converted_domain = to_ascii_domain(m.group(1)) if m else None
            if converted_domain:
                pattern = "||" + converted_domain + m.group(2)
            else:
                stats["non-ascii"] += 1
                continue

        cond_extras, priority, drop = parse_options(option_str)
        if cond_extras is None or drop in ("unsupported-option", "unknown-option", "empty-domain-option"):
            stats["unsupported"] += 1
            continue
        if drop == "cosmetic-only":
            stats["cosmetic"] += 1
            continue

        pattern_lower = pattern.lower()

        # Batch the two overwhelmingly common shapes into requestDomains rules.
        if not is_exception and priority == 1:
            m = DOMAIN_RULE_RE.match(pattern_lower)
            if m and not option_str:
                plain_block_domains.append(m.group(1))
                continue
            if m and cond_extras == {"domainType": "thirdParty"}:
                plain_3p_block_domains.append(m.group(1))
                continue

        condition = {"urlFilter": pattern_lower}
        condition.update(cond_extras)
        if "isUrlFilterCaseSensitive" not in condition:
            condition["isUrlFilterCaseSensitive"] = False

        if is_exception:
            # A $document exception whitelists the whole page.
            if cond_extras.get("resourceTypes") == ["main_frame"]:
                action = {"type": "allowAllRequests"}
            else:
                action = {"type": "allow"}
                priority = max(priority, 2)
        else:
            action = {"type": "block"}

        rules.append({
            "id": alloc_id(),
            "priority": priority,
            "action": action,
            "condition": condition,
        })
        stats["converted"] += 1

    for domains, extra in ((plain_block_domains, {}), (plain_3p_block_domains, {"domainType": "thirdParty"})):
        for i in range(0, len(domains), BATCH_SIZE):
            chunk = sorted(set(domains[i:i + BATCH_SIZE]))
            condition = {"requestDomains": chunk}
            condition.update(extra)
            rules.append({
                "id": alloc_id(),
                "priority": 1,
                "action": {"type": "block"},
                "condition": condition,
            })
        stats["converted"] += len(domains)

    return rules, stats


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, dst = sys.argv[1], sys.argv[2]
    with open(src, encoding="utf-8") as f:
        rules, stats = convert(f)
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(rules, f, separators=(",", ":"))
    print(f"{src} -> {dst}: {len(rules)} DNR rules "
          f"(covering {stats['converted']} source filters)")
    print("  skipped:", {k: v for k, v in stats.items() if k != "converted" and v})


if __name__ == "__main__":
    main()
