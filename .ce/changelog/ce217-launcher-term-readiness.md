---
slug: ce217-launcher-term-readiness
date: 2026-06-24
kind: fixed
scope: DGX/VPS runsc launchers
issue: ce-ops#217
---

Hardens the DGX and VPS runsc launchers for Phase-1 herdr launches.

- Coerces empty or `dumb` host `TERM` values to `xterm-256color` before Docker
  argv construction, preventing `TERM=dumb` from appearing in dry-run output.
- Changes detached readiness polling to require the herdr socket inside the
  container and a successful `HERDR_SOCKET_PATH=<socket> herdr pane list` with
  at least one pane, avoiding false negatives when herdr is already serving.
