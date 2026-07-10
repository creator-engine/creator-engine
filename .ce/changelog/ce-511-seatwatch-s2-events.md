---
slug: ce-511-seatwatch-s2-events
date: 2026-07-10
kind: added
scope: seat-watch daemon slice 2 events
issue: ce-ops#511
work_class: S
---

**Add seat-watch slice 2 detector event durability.**

Seat-watch now persists `idle-without-signal` and `dispatch-undelivered`
detections as structured JSONL records under the daemon state root, with
`seat_id`, `class`, `evidence`, and `timestamp` fields. Adds a supervised
systemd example for restart-on-failure posture and focused unit coverage for
the detector ledger and exit-code expectations.
