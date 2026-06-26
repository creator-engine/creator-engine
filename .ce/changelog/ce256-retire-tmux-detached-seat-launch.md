---
slug: ce256-retire-tmux-detached-seat-launch
date: 2026-06-26
kind: changed
scope: deploy/runsc codex seat launchers
issue: ce-ops#256
---

Retire the host-tmux anchor from Codex seat launch.

- Makes the VPS and DGX Codex runsc launchers default to detached
  `docker run -d --name ...` with foreground mode retained behind
  `--foreground` / `CE_*_FOREGROUND=1`.
- Removes the detached-mode container TTY default; herdr owns the in-container
  PTY, with `CE_*_TTY_FLAGS` still available for explicit diagnostics.
- Adds a systemd seat container template that starts detached launchers and
  applies Docker `--restart=unless-stopped` for supervised container restart.
- Documents no-host-tmux herdr verification and covers detached command
  generation, restart policy, foreground migration, and tmux absence in unit
  tests.
