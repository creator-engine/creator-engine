# BRIEF — dev-3 — BATCH 3 (three units, U2/U3 read-only and safe to run concurrent with U1)
2026-07-06 ~10:4xZ by CE-DEV-2. You are a FOREMAN: fan these out to workers where safe. Contained seat, git egress only (no gh CLI, no curl — all needed facts are embedded below).

## U1 — unblock #467 version-drift gate (your BLOCKED unit; priority)
Worktree /var/tmp/ce-467-version-drift-gate, branch ce-467-version-drift-gate, commit 9164627e. You reported 12 suite-wide pytest failures with focused drift tests green. Triage:
1. Run the same failing subset on a CLEAN origin/main worktree in your container env. If they fail there too → pre-existing/env, NOT yours: capture exact test ids + tracebacks as evidence, then run the exact bar `ce validate-pr --declared-work-class story` to completion; if it fails ONLY on those same env failures, signal `BLOCKED-ENV ce-467 <commit> <evidence-path>` — controller re-arbitrates host-side at harvest.
2. If the failures are introduced by your diff → fix them, re-run full validate-pr to GREEN, regen carrier (stem == branch slug), signal `READY <sha>`.
CONSTRAINT (territory): dev-1 owns the 0.3.3 docs/README version-currency sweep (branch ce-docs-version-currency-0-3-3, in flight). If your gate flags stale version refs in docs/README, use your allowlist/annotation mechanism — do NOT edit those docs files yourself.

## U2 — review-analysis of PR #859 (dev-1's fix: add merge_group trigger to adoption workflow template, ce-ops#473)
Read-only. Fetch the PR branch via git only: `git fetch origin pull/859/head:review-859` in a THROWAWAY worktree. Baseline STRICTLY via `git show <merge-base>:<path>` — NEVER compare against any root checkout.
Embedded main-side facts (verified by controller): validators/creator_engine_validator/onboard_apply.py on origin/main emits only `pull_request` + `push` triggers in the client workflow template; our own .github/workflows/validate.yml carries `merge_group: types: [checks_requested]`. The fix should mirror that stanza into the emitted template + a failure-direction unit test (test fails on old template) + doc currency if any doc states the trigger set. Work class declared: tiny.
Bars: correctness of the emitted YAML, test failure-direction proven, no scope creep, no sha-pinned files touched, carrier/changelog present, class sane.
Note: your own #461 unit is gated on this PR merging. You are NOT its author so reviewing it is legitimate — but review on the evidence only.
Emit exactly: `VERDICT-859: APPROVE` or `VERDICT-859: REQUEST_CHANGES` + numbered evidence.

## U3 — review-analysis of PR #861 (dev-1's ce-ops#459: harden client CI SHA256SUMS verification)
Read-only, same mechanics: `git fetch origin pull/861/head:review-861`, throwaway worktree, merge-base baseline only.
Controller pre-verified and you may take as given: head = 636c028f8b905227d84fd6bb3a63e4ed6907d857; touched files = validators/creator_engine_validator/onboard_apply.py, validators/tests/unit/test_onboard_apply.py, carrier + changelog ONLY (no sha256-pinned files, so non-release-class is confirmed).
Your job is the substance: does the hardening actually verify SHA256SUMS correctly in the emitted client CI (failure direction: tampered artifact MUST fail), are the tests real (fail on old behavior), any injection/quoting hazards in emitted shell, class (tiny) sane.
Emit exactly: `VERDICT-861: APPROVE` or `VERDICT-861: REQUEST_CHANGES` + numbered evidence.

## Standing rules
FULL preflight bar per playbooks/controller/briefs/dispatch.md (U1 only; U2/U3 produce verdicts, not commits). COMMIT-ONLY → harvest; never push, approve, merge, or sign. Stop lines standard. Report each unit's terminal signal on its own line.
