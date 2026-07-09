---
slug: ce-512-redeploy-portability
date: 2026-07-09
kind: changed
scope: deploy/singleton-redeploy
issue: ce-512
---

**Make singleton redeploy portable across deployment hosts.**

- Added service-user rendering for the queue daemon systemd unit.
- Kept linked worktree checkout validation compatible with the daemon container
  mount model.
- Updated the health probe path to compose rendered unit `Environment=` values
  with the host env file, including OpenBao CA handling.
- Rewrote the relocation runbook with parameterized host, user, path, state, and
  OpenBao settings.
- Kept `container_launcher.py` in the portability plane manifest so future
  launcher path changes remain covered by the portability guard.
