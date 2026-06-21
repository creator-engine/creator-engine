---
slug: ce39-merge-queue
date: 2026-06-21
kind: added
scope: forge coordination / merge queue
base: 1b09d1b6
---

Lands the path to GitHub's native merge queue on `main` to retire the
rebase→re-review tax (ce-ops#39): a rebase force-push currently dismisses the
human approval, so a serial merge train pays a fresh code-owner review per step.

- **`merge_group` required-CI trigger (load-bearing).** `validate.yml` now
  triggers on `merge_group: { types: [checks_requested] }` alongside
  `pull_request`/`push`, so the "Validate governance artifacts" required check
  reports on the queue's temporary `gh-readonly-queue/*` branch — without it the
  queue would stall forever. The `path-manifest PR-diff gate` stays
  `pull_request`-only (no carrier diff on the synthetic merge commit). Guarded by
  `test_workflow_merge_group_trigger.py`.
- **Opt-in `merge_queue` rule on `RulesetPolicy`** so the queue is enabled
  through the existing `upsert_ruleset` forge adapter (plan-by-default,
  idempotent, verify-on-apply). Defaults to `require_merge_queue=False`, leaving
  every existing policy byte-unchanged; the queue merge method is validated
  against the squash-only floor.
- **F6 adjudicated:** the merge head-pin is conserved by machine
  tree-equivalence + the append-only evidence chain (TESTED==MERGES), **not** by
  a `ce-root-v1` signature over the head — so the queue needs no new key and no
  CI-resident key. Design + the precise (negative) key-custody decision for
  Operator ratification: `GITHUB_NATIVE_COORDINATION_PROTOCOL.md` §g.
- **Enablement runbook** (gated, not executed):
  `MERGE_QUEUE_ENABLEMENT_RUNBOOK.md`.

Rebuilds the wheelhouse app wheel + `SHA256SUMS` (mechanical co-move forced by
`verify_wheel_matches_source` over `forge/ruleset.py`). No queue/Rulesets/branch
-protection change is applied by this PR — those are gated controller/Operator
actions.
