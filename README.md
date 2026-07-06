# My Ad Blocker

A minimal, self-built Chrome ad blocker based on the Manifest V3 `declarativeNetRequest` API, with full **EasyList** and **EasyPrivacy** coverage converted to native Chrome rule format.

The extension code is ~100 lines with zero dependencies. It never requests permission to read your page content — filtering is declarative and executed by the browser engine itself. You can audit every line, and nobody can push a malicious update to you.

## File structure

| File | Purpose |
|------|---------|
| `manifest.json` | Extension manifest (permissions, rulesets, content script, popup) |
| `rules_easylist.json` | EasyList converted to declarativeNetRequest rules (ads) |
| `rules_easyprivacy.json` | EasyPrivacy converted to declarativeNetRequest rules (trackers) |
| `rules_custom.json` | Your own hand-written rules |
| `hide-ads.css` | Cosmetic filtering (hides leftover empty ad containers) |
| `popup.html` / `popup.js` | Toolbar popup with per-ruleset on/off toggles |
| `tools/convert.py` | Converter: Adblock Plus filter syntax → MV3 rule JSON |
| `tools/update-lists.sh` | One-command refresh of the EasyList/EasyPrivacy rule files |

## Installation

This is an unpacked extension for personal use — no Chrome Web Store required:

1. Open Chrome and navigate to `chrome://extensions`
2. Enable **Developer mode** (top-right toggle)
3. Click **Load unpacked** (top-left)
4. Select this folder (`my-adblocker/`)
5. Done. The icon appears in the toolbar (it may be tucked into the puzzle-piece menu — pin it if you like)

> **Note:** An unpacked extension is bound to its folder path. Do not move or delete this folder, or the extension will stop working. Chrome may occasionally remind you about developer-mode extensions on startup — click "Keep" to dismiss.

### Verifying it works

Open any ad-heavy news site, press F12 → **Network** tab, and reload. Requests to domains like `doubleclick.net` or `googlesyndication.com` should show up in red as `(blocked:other)`.

## Daily use

- **Toggle rulesets**: click the toolbar icon. Each ruleset (Custom / EasyList / EasyPrivacy) can be enabled or disabled independently and takes effect immediately. The cosmetic CSS is not affected by these toggles.
- **A site broke?** Pause the rulesets via the popup and reload to confirm the blocker is the cause. If it is, see "Whitelisting a site" below.

## Configuration

After editing any file, go back to `chrome://extensions` and click the **reload (↻) icon** on the extension card. Then reload any open tabs.

### Updating the filter lists

The bundled EasyList/EasyPrivacy snapshots are current as of the commit date. Upstream, both lists change daily (new ad domains, false-positive fixes), so refresh them every week or two:

```bash
tools/update-lists.sh
```

The script downloads the latest lists, converts them, verifies the total stays under Chrome's guaranteed 30,000-rule limit, and only then replaces the rule files — a failed download can never leave you with corrupt rules. Afterwards, reload the extension at `chrome://extensions` (Chrome only reads static rule files at load time, so this last click cannot be automated).

To run it automatically, add a cron entry (`crontab -e`):

```cron
# Refresh filter lists every Monday at 09:00
0 9 * * 1 /home/roger/my-adblocker/tools/update-lists.sh >> /tmp/adblock-update.log 2>&1
```

You'll still need to click reload in Chrome once after each refresh.

Under the hood, `tools/convert.py` handles the standard network-filter syntax (`||domain^`, `$third-party`, `$script`, `$domain=`, `@@` exceptions, ...) and skips what declarativeNetRequest cannot express (cosmetic rules, regex filters, `$csp`, `$redirect`, `$removeparam`, `$popup`); it prints a summary of what was converted and skipped.

### Adding your own blocking rules

Edit `rules_custom.json`. To block another ad domain (subdomains included), add it to the `requestDomains` array of rule 1:

```json
"requestDomains": [
  "doubleclick.net",
  "new-ad-domain.com"
]
```

To add a different kind of rule, append a new object with a unique `id`:

```json
{
  "id": 3,
  "priority": 1,
  "action": { "type": "block" },
  "condition": {
    "urlFilter": "/ads/banner/",
    "resourceTypes": ["image", "script"]
  }
}
```

Common `urlFilter` syntax:
- `||example.com^` — all requests to the domain and its subdomains
- `/ads/` — URL path contains `/ads/`
- `*` — wildcard

Full reference: [Chrome declarativeNetRequest documentation](https://developer.chrome.com/docs/extensions/reference/api/declarativeNetRequest).

### Whitelisting a site

If blocking breaks a site, add an `allow` rule to `rules_custom.json` with a higher `priority` than the block rules:

```json
{
  "id": 100,
  "priority": 10,
  "action": { "type": "allow" },
  "condition": {
    "initiatorDomains": ["site-to-whitelist.com"]
  }
}
```

### Hiding more ad elements

Edit `hide-ads.css`. To find a selector: right-click the ad → **Inspect**, find the ad container's `id` or `class`, and add it:

```css
.some-ad-class,
#some-ad-id {
  display: none !important;
}
```

> Beware of overly broad selectors (e.g. `.ad` will also hide legitimate elements that happen to use that class name).

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Rule changes don't take effect | Click reload (↻) on `chrome://extensions`, then reload the page |
| Extension card shows a red "Errors" badge | Open it — usually a JSON syntax error in a rules file (trailing comma, duplicate `id`) |
| A site's layout broke | Pause via the popup to confirm; add an `allow` rule if it's network blocking, or remove the CSS selector if it's cosmetic |
| Ads still showing | F12 → Network, find the ad request's domain, add it to `rules_custom.json` |
| Ruleset fails to enable | Chrome guarantees 30,000 static rules and this extension ships ~13,500, so it fits; if you add more lists, watch the total |

## Limitations (by design)

- No cosmetic filtering from EasyList — element hiding uses only the small hand-written `hide-ads.css`. Sites may show empty placeholder boxes where ads used to be.
- Cannot block YouTube in-video ads or first-party ads (served from the same domain as the content).
- No anti-adblock countermeasures — some sites will detect blocking and complain.
- Regex filters and `$csp`/`$redirect`/`$removeparam` filters from EasyList are skipped (declarativeNetRequest cannot express them; they are a small fraction of the list).

## Licensing and attribution

- Extension code (`manifest.json`, `popup.*`, `hide-ads.css`, `tools/convert.py`): MIT.
- `rules_easylist.json` and `rules_easyprivacy.json` are derived from [EasyList and EasyPrivacy](https://easylist.to/), © The EasyList authors, dual-licensed under [GPLv3](https://www.gnu.org/licenses/gpl-3.0.html) and [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/). These files remain under those licenses.
