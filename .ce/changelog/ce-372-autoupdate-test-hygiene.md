---
slug: ce-372-autoupdate-test-hygiene
date: 2026-06-30
kind: changed
scope: signed updater tests
issue: ce-ops#372
---

**Auto-update startup notice test hygiene.**

- **Declared work class:** tiny
- Replaced the startup notice test's hardcoded cache path with pytest tmp_path.
- Added cached notice_shown coverage so a fresh shown cache suppresses a second notice.
