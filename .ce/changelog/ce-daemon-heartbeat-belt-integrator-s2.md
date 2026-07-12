---
slug: ce-daemon-heartbeat-belt-integrator-s2
date: 2026-07-12
kind: added
scope: belt and integrator daemon liveness
issue: none
---

**feat(daemons): belt and integrator heartbeat adoption (S2).**

- Adopt the passive daemon-heartbeat contract for the belt and integrator daemons, including startup, running, pass-complete, and terminal lifecycle records.
- Keep the belt as its existing per-invocation systemd loop: each invocation resumes the prior heartbeat index, avoiding a broader CLI-loop redesign.
- Record stopping or failed terminal heartbeats for belt, integrator, and review-pickup exits without changing their operational authority.
