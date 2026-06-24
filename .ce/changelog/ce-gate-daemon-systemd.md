---
slug: ce-gate-daemon-systemd
date: 2026-06-24
kind: added
scope: deploy/systemd
issue: ce-gate-daemon-systemd
---

Added source-run systemd support for the autonomous gate daemons.

- Added checked-in systemd unit templates for the Integrator `queue-daemon` and
  review-pickup daemon, with env-file parameterization for repo and tokens.
- Added an idempotent installer that renders units to user or system systemd,
  runs daemon reload, enables services, and starts them unless `--no-start` is
  supplied.
- Added short operator docs and offline parser/lint tests for the unit files.
