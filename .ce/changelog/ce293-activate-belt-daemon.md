---
slug: ce293-activate-belt-daemon
date: 2026-06-27
kind: added
scope: deploy/systemd
issue: ce-ops#293
work_class: story
---

**feat(ce-ops#293): activate observe-only belt daemon unit**

- **Declared work class:** story

Added a systemd unit for the work-pickup conveyor belt in observe-only mode.
The unit loops the one-shot `ce pickup poll` command with `CE_BELT_IDENTITY`,
`CE_GATE_REPO`, optional `CE_BELT_INTERVAL_SECONDS`, and optional
`CE_BELT_LABELS`; it does not pass `--claim`, `--enable-launch`, or ambient
`gh` auth.

Updated the gate daemon installer, operator docs, focused systemd tests, and
captured live observe-only run evidence.
