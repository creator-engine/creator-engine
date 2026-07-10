---
slug: ce-510-ship-gate-s2
type: implementation
scope: release acceptance gate mechanics
---

Adds the release-acceptance state machine mechanics for RC ship-gating.

- Models repository-visible release-acceptance records and governed state
  transitions for candidate promotion through closure.
- Fails closed when rehearsal evidence lacks RC identity fields needed for
  promotion binding.
- Adds pure closure-integrity checks so release-ticket closure requires linked
  acceptance evidence and persistent-state probes for deploy-class claims.
