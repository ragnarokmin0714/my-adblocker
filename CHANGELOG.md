# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and this project adheres to
[Semantic Versioning](https://semver.org/).

## [1.2.0]

### Added
- Icon set: master `icons/icon.svg` and exported `icon16/48/128.png`, wired into
  the manifest (`icons` and `action.default_icon`).
- Logo mark shown in the toolbar popup header.

### Changed
- Renamed the extension to **GlassBlock**.

## [1.1.0]

### Added
- Full **EasyList** and **EasyPrivacy** coverage, converted from Adblock Plus
  filter syntax to native `declarativeNetRequest` rules
  (`rules_easylist.json`, `rules_easyprivacy.json`).
- `tools/convert.py` — converter that turns filter lists into MV3 rule JSON,
  batching plain domain rules to stay well under Chrome's static-rule limit.
- `tools/update-lists.sh` — one-command refresh that downloads, converts, and
  rule-count-checks the lists atomically before replacing the shipped files.
- Per-ruleset on/off toggles in the toolbar popup (Custom / EasyList /
  EasyPrivacy), each taking effect immediately.

### Changed
- Renamed `rules.json` to `rules_custom.json` to sit alongside the two
  upstream-derived rulesets.
- All UI text, code comments, and documentation translated to English.

## [1.0.0]

### Added
- Initial release: minimal Manifest V3 ad blocker using
  `declarativeNetRequest` for network blocking and a content-script CSS file
  (`hide-ads.css`) for cosmetic element hiding.
- Hand-written `rules.json` covering core ad domains.
