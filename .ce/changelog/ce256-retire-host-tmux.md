---
slug: ce256-retire-host-tmux
date: 2026-06-26
kind: changed
scope: runsc Codex seat launch supervision
issue: ce-ops#256
---

**retire host tmux anchoring for runsc Codex seats.**

- DGX and VPS runsc launchers keep detached `docker run -d` as the default and
  make the TTY default branch explicit for detached versus legacy foreground
  launches.
- The Codex seat systemd template now supervises the detached container by
  waiting on it in the foreground, removing stale named containers before
  restart, and using systemd restart policy instead of a host tmux anchor.
- Unit coverage pins the systemd supervision contract.
