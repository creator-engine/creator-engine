---
slug: ce-codex-statusline-default
date: 2026-06-25
kind: added
scope: codex seat statusline default
issue: ce-ops#244
---

**default codex TUI statusline for contained CE seats.**

- Add a [tui] status_line block to the generated codex config in both runsc launchers so contained codex CE seats boot with the statusline by default (picked up on next canonical relaunch).
