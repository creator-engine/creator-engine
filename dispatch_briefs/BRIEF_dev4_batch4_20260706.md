# BRIEF — dev-4 batch 4 — 2026-07-06 ~14:1xZ — 3 units (2 author round-fixes + 1 review)

Foreman: run U1/U2/U3 as concurrent workers where file-disjoint (U1 and U2 touch different
modules; U3 is read-only). Commit-only mode: NO push. Per unit, signal on completion:
`READY <branch> <sha> <evidence-path>` or `BLOCKED-ENV <branch> <sha> <evidence-path>`.
REVIEW VERDICTS: write the full numbered evidence (file:line per finding) to a FILE under
/var/tmp/ — pane buffers have eaten verdict evidence twice today. Stop line per unit: do NOT
touch approval/merge paths, do NOT sign anything; if a required signature is invalid, report —
controller signs.

## U1 — PR #865 round-2 fix (you authored round-1; branch `ce-474-verify-reference-mode`)
Reviewer verdict REQUEST_CHANGES, findings verbatim (fix BOTH):
1. `validators/creator_engine_validator/onboard_apply_live.py:2145-2160` accepts any nonzero gh
   failure as documented-not-enforced when declared_protections == "reference" if
   `protection_floor_unenforceable(parsed, stderr)` returns true. The classifier
   (`forge/protection_diagnostics.py:56-65`) does not require an actual HTTP 403 — text like
   "make this repository public" / "upgrade" suffices. A crafted non-403 body with those
   strings, or a plan-shaped HTTP 502, bypasses preserved-check enforcement. Required:
   demand a real 403 (or equivalently strong signal) before accepting documented-not-enforced;
   crafted API bodies and non-403 errors must stay fail-closed.
2. Add the missing failure-direction test: declared-reference where the body contains
   plan/remediation markers while stderr/status is non-403 → must stay fail-closed.
   (Existing coverage: test_onboard_apply_live.py:1677-1699 = 403 path; :1718-1728 = generic 502.)
Update branch from the PR head: `git fetch origin pull/865/head` and build on that exact head.

## U2 — PR #864 round-3 fix (you authored; branch `ce-426-g11-reviewer-authority-minting`)
Round-2 closed TTL/single-use + self-review refusal + brain re-pin. ONE blocker remains:
3. An `independent_review_venue` envelope still covers approval-capable `gh pr review --approve`.
   `_authority_covers` only rejects raw `gh api`/curl approve paths, then allows matching
   `pr_review` by PR at `hook_check.py:1122-1140`. Existing test
   `test_hook_check_reviewer_authority.py:50-52` asserts `gh pr review 106 --approve` is ALLOWED
   under a matching envelope. Required: capability-bound the review-venue envelope AWAY from
   approval — approve must require distinct authority; flip that test's expectation and add the
   failure-direction test (envelope-holder attempting --approve → refused).
Build on the PR head: `git fetch origin pull/864/head`.

## U3 — REVIEW PR #868 (non-author: dev-3 authored) — work_claims lifecycle (ce-ops#476 seed)
Fetch: `git fetch origin pull/868/head`. Baseline = merge-base vs origin/main, compare via
`git show <merge-base>:<path>` ONLY (never your checkout's working tree).
Review bars (state machine is dark-factory infra — strict):
- Lifecycle states must be a closed set with legal-transition enforcement (no free-form writes).
- Claim release/expiry must not be forgeable by the claiming seat itself.
- Merge closeout must be idempotent and evidence-linked.
- Tests must cover illegal-transition refusal (failure direction), not just happy path.
Emit `VERDICT-868: APPROVE|REQUEST_CHANGES` + write full evidence to /var/tmp/verdict-868.md.
