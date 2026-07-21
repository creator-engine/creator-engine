---
slug: t4-policy-flip
date: 2026-07-21
kind: changed
scope: governance
issue: T4
---

**Retire mandatory local full validation policy.**

- Retire full local `ce validate-pr` as a standing progression prerequisite while preserving it as an optional diagnostic.
- Make pushed current-head required Validate status, independent review, and ratification authoritative evidence.
- Record the 2026-07-21 evidence: a 28-minute local run produced an unusable environmental claim and a dead child consumed 2h18m, while CI validated the respective deltas in under 10 minutes.
- Ordering satisfied: the CI-migration change is already present in this
  branch's base (`7592e082`), so the policy flip cannot create an unguarded
  invariant window.
- Residual: runtime defaults in conveyor, conveyor daemon, and release orchestration remain separately scoped.
