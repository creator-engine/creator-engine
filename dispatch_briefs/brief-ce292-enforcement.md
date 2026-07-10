# WORK CLAIM — ce-ops#292 enforcement hardening (AutoReview "never-APPROVE" guard)

**Seat:** dev-4 (DGX build seat). **Role:** implementer-foreman.
**You are born a foreman** — fan subtasks out to your own threads/workers where it helps; do not single-thread everything inline.

## Branch
Start clean off the latest main:
```
git fetch origin && git checkout -b ce-292-autoreview-enforcement origin/main
```
(You are currently on the stale `ce11-test-tier-split` — do NOT build there.)

## Why (self-contained — do not rely on reading ce-ops)
PR #592 implemented ce-ops#292 (a self-firing reviewer that auto-runs `/code-review` pre-PR/pre-merge). An independent review found a **BLOCKING** defect: the critical safety property "the self-fire reviewer must NEVER emit APPROVE" is **prompt-instruction-only** — there is no mechanical guard. The self-fire path posts review verdicts via a raw `gh api -X POST .../reviews` call with a JSON body, and the existing PreToolUse reviewer-authority hook only guards `gh pr review --approve`, NOT the raw `gh api` path. `.claude/agents/reviewer.md` also still lists `APPROVE` as a valid verdict. A self-approving review would defeat the merge gate.

## Task — add mechanical enforcement
1. **Hook guard:** add/extend a PreToolUse hook that DENIES any `gh api` call to the `/reviews` endpoint carrying `"event":"APPROVE"` from the self-fire/reviewer context. Mirror the existing `gh pr review --approve` guard — find it via `validators/tests/unit/test_hook_check_reviewer_authority.py` and the hook it exercises.
2. **Charter alignment:** scope `.claude/agents/reviewer.md` (and the `/code-review` self-fire wrapper in `.claude/commands/code-review.md`) so a self-fire reviewer cannot return/post `APPROVE`.
3. **Behavioral test (not a text grep):** add a test proving an attempted `APPROVE` on the self-fire path is actually denied/blocked at runtime — not merely that the prose forbids it.

## Allowed paths (nothing else)
`validators/**` (hook + tests), `.claude/agents/reviewer.md`, `.claude/commands/code-review.md`, `.ce/changelog/**`, `.ce/pr-manifests/**`.

## Evidence (DoD)
Run the FULL local preflight `ce validate-pr` (CI-parity, full suite — NOT `-m "not slow"`) and capture it GREEN. Declare the work-size class the G5 size gate will DERIVE (rename/relocation-aware — relocations count delete+add; see the rule behind ce-ops#335), not the optimistic tier.

## Stop-line
- Preflight GREEN + self-push works → push `ce-292-autoreview-enforcement` and open ONE PR referencing ce-ops#292 (note: "enforcement follow-up to #592"). Do NOT approve / merge / enqueue.
- Preflight GREEN but push FAILS (contained-seat auth gap, ce-ops#337) → STOP and report exactly: `READY-FOR-HARVEST: branch ce-292-autoreview-enforcement, <N> commits, preflight GREEN` so the controller harvests.
- Preflight RED → STOP and report the failing gate. Do not thrash.
