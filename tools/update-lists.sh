#!/usr/bin/env bash
# Refresh rules_easylist.json / rules_easyprivacy.json from the upstream lists.
# Safe to run from anywhere (including cron): downloads and converts into a
# temp dir first, and only replaces the shipped rule files if every step
# succeeded, so a network failure can never leave you with corrupt rules.
set -euo pipefail
cd "$(dirname "$0")/.."

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

echo "Downloading filter lists..."
curl -sSL --fail --max-time 120 -o "$tmp/easylist.txt"    https://easylist.to/easylist/easylist.txt
curl -sSL --fail --max-time 120 -o "$tmp/easyprivacy.txt" https://easylist.to/easylist/easyprivacy.txt

python3 tools/convert.py "$tmp/easylist.txt"    "$tmp/rules_easylist.json"
python3 tools/convert.py "$tmp/easyprivacy.txt" "$tmp/rules_easyprivacy.json"

# Chrome guarantees only 30,000 static rules across all enabled rulesets.
python3 - "$tmp" <<'EOF'
import json, sys
tmp = sys.argv[1]
total = len(json.load(open("rules_custom.json")))
for f in ("rules_easylist.json", "rules_easyprivacy.json"):
    total += len(json.load(open(f"{tmp}/{f}")))
if total > 30000:
    sys.exit(f"ABORTED: {total} total rules exceeds Chrome's guaranteed 30,000 limit")
print(f"Total rules: {total} / 30000")
EOF

mv "$tmp/rules_easylist.json"    rules_easylist.json
mv "$tmp/rules_easyprivacy.json" rules_easyprivacy.json

echo "Done. Reload the extension at chrome://extensions (click the ↻ icon) to apply."
