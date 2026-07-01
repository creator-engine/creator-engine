---
slug: ce-351-queue-daemon-relocation
date: 2026-07-01
kind: added
scope: deploy/queue-daemon
issue: ce-ops#351
---

**Durable queue daemon relocation package.**

- Added a boot-persistent systemd unit for the merge-queue daemon with
  `Restart=always`, journald logging, OpenBao address wiring, and secret loading
  through a host-only environment file.
- Added a fail-closed launcher with `--health` checks for daemon liveness,
  GitHub token validity, and OpenBao token validity.
- Added a controller runbook for CE-DEV-1 cutover, approval auto-merge
  verification, DGX retirement, and rollback to DGX.
