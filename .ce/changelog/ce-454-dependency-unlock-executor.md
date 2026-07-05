---
slug: ce-454-dependency-unlock-executor
date: 2026-07-05
kind: feature
scope: validator
issue: creator-engine/ce-ops#454
---

**Merge-triggered dependency-unlock executor, SHADOW-first (slice 1).**

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
  `ce --help` and the generated CLI reference, mirroring `triage`); update the
  CLI-inventory companion guard in `test_v1_docs_reconciliation.py`.
- Add `.github/workflows/ce-dependency-unlock.yml`: triggers on
  `pull_request` `closed` (gated `merged == true && base.ref == 'main'`),
  fail-open on an absent `CE_CROSS_REPO_TOKEN`, and uploads a JSON audit
  artifact on every run. SHADOW is the only mode this PR ships enabled: no
  repo variable enables live mode.
- Add `validators/tests/unit/test_dependency_unlock.py` (32 cases, fake
  `GhRunner`, zero network) covering dedup, fail-closed parsing, non-dependency
  holds, zero write calls in shadow mode, kill-switch precedence, and the
  closed-without-merge matrix.
- Supersede the stale `brain-assertion-d1b-09-ce-cli-doc-coupling` evidence
  pin (v3 -> v4) via `ce brain correct`, since editing
  `test_v1_docs_reconciliation.py` changed its whole-file evidence_sha256;
  bumps the `test_ce_brain_drift.py` active-count ratchet 89 -> 90.
- Does not touch `work_claims.py` (stretch piece-4 is out of this unit).
