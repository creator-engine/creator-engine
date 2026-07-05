---
slug: ce-brownfield-refusal-message
date: 2026-07-05
kind: fixed
scope: validator cli
---

**Distinguish brownfield adoption credential-resolution refusals.**

- Kept the no-escalation brownfield apply refusal text unchanged.
- Added a distinct refusal when the dual adoption escalation env vars are set but App credentials cannot resolve, with remediation for `kind: own` PEM and `kind: shared` broker setups.
