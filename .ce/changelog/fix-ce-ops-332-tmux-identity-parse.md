---
slug: fix-ce-ops-332-tmux-identity-parse
date: 2026-06-27
kind: fixed
scope: tmux adapter (Gate 3 visible-lane terminal seam)
issue: ce-ops#332
---

**Robust tmux pane-identity parsing across tab-sanitizing tmux builds.**

- `ce launch` crashed with `TmuxError: could not parse tmux identity` on tmux
  builds (e.g. tmux 3.4 on some Ubuntu 24.04 installs) that sanitize the literal
  TAB delimiter in `-F` output to an underscore. The behavior is build/
  environment dependent, not version dependent, so it cannot be guarded by a
  version check.
- `_parse_identity` now normalizes the separator (TAB or `_`) before splitting,
  recovering the five identity fields under both tmux behaviors. The fix is at
  the single shared parse seam, so both pane-spawn paths (`new-session` and
  `new-window`) are covered.
- Adds parametrized `_parse_identity` unit tests over tab-separated and
  underscore-sanitized real-shaped output, an end-to-end `ensure_pane` test on a
  sanitizing tmux, and an unparseable-output regression guard.
