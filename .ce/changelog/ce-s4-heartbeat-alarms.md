---
slug: ce-s4-heartbeat-alarms
date: 2026-07-12
kind: added
scope: daemon liveness alarms
issue: none
---

**feat(daemons): add heartbeat alarm consumer (S4).**

- Classify validated daemon heartbeat records and emit bounded, secret-free alarm evidence for stale or failed daemons.
- Add a five-minute user timer without changing long-running gate-daemon supervision.
