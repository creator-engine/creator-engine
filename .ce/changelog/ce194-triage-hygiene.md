---
slug: ce194-triage-hygiene
ticket: ce-ops#194
type: fix
scope: forge triage hygiene
---

Tightens `ce pickup triage` candidate hygiene so the planner fails closed on
non-claimable or ambiguous issue work.

- Skips issues with open PR references, closed/done state, held/checkpoint
  labels, arc held-checkpoint refs, and aggregate arc/epic/meta shape before
  surfacing pickup mutations.
- Keeps invalid-arc refusal, readiness blockers, assignment skips, and active
  work-claim collision checks intact.
- Adds offline unit coverage for PR reference collision, lookup failure,
  closed/done, held labels, arc held-checkpoints, and meta issues.
