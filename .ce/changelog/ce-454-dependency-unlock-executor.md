---
slug: ce-454-dependency-unlock-executor
date: 2026-07-05
kind: feature
scope: validator
issue: creator-engine/ce-ops#454
---

**Merge-triggered dependency-unlock executor (slice 1, SHADOW-first).**

- Add `creator_engine_validator.dependency_unlock`, a pure evaluator (injectable
  `GhRunner`, no import-time I/O) that implements
  `docs/contracts/dependency-unlock.md` for exactly one re-evaluation event: a
  pull request merging into `main`. Blocker-reference parsing reuses (never
  reimplements) `forge_triage.readiness_blockers`,
  `forge_triage._BLOCKING_LABEL_PREFIXES`, `forge_triage._DEPENDENCY_FIELDS`,
  and `forge_triage._extract_issue_refs`/`_DEPENDENCY_BODY_RE`.
- Implement the CLOSED-WITHOUT-MERGE rule verbatim: a pull-request blocker
  resolves iff `merged is True`; an issue blocker resolves iff
  `state == "closed" and state_reason == "completed"`. Everything else
  (closed unmerged, `not_planned`, unknown, inaccessible) stays blocking,
  fail-closed.
- Add `ce dependency-unlock scan` (new INTERNAL command group, hidden from
  `ce --help` and the generated CLI reference, mirroring `triage`).
- Add `.github/workflows/ce-dependency-unlock.yml`: triggers on
  `pull_request` `closed` (gated `merged == true && base.ref == 'main'`),
  fail-open on an absent `CE_CROSS_REPO_TOKEN`, and uploads a JSON audit
  artifact on every run. SHADOW is the only mode this PR ships enabled: no
  repo variable enables live mode. `CE_DEP_UNLOCK_RUN_MODE == 'live'` would
  enable apply; `CE_DEP_UNLOCK_KILL_SWITCH` truthy always forces shadow
  regardless.
- Add `validators/tests/unit/test_dependency_unlock.py` (32 cases, fake
  `GhRunner`, zero network): dedup-on-duplicate-search-hit, fail-closed on
  unparseable/ambiguous blocker refs, non-dependency hold labels blocking
  despite resolved deps, zero write calls in shadow mode, kill-switch forcing
  shadow over `RUN_MODE=live`, and the closed-without-merge matrix (PR closed
  unmerged / issue closed not-planned / issue closed completed).
- Does not touch `work_claims.py` (stretch piece-4, lifecycle states, is
  explicitly out of this unit).
