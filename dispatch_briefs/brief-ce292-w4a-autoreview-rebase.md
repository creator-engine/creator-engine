# WORK CLAIM — ce-ops#292 / PR #592 — AutoReview never-APPROVE: rebase + behavioral guard test

**Seat:** dev-3. **Role:** implementer-foreman. **Born foreman** — fan out to your own worker threads; do NOT inline.

## Branch (the PR #592 branch already exists; you originally authored it)
```
git fetch origin
git checkout -B ce-292-autoreview origin/ce-292-autoreview
git rebase origin/main          # picks up the #596 runtime guard (commit ca496fb1)
```
If the rebase conflicts, resolve preserving BOTH the #596 guard and your AutoReview self-trigger logic.

## Why (self-contained)
PR #592 (AutoReview self-trigger) is **CHANGES_REQUESTED**. The blocking reason from the independent re-review:
> The 'never APPROVE' safety property is **not mechanically enforced**. It is stated in prose (AGENTS.md, code-review.md, changelog) and 'tested' only by grepping the command *text*; there is no runtime guard on the self-fire path that uses `gh api -X POST .../reviews`.
Since that review, commit **`ca496fb1` (#596)** landed on `main`: it blocks a raw `gh api ... event=APPROVE` on the AutoReview self-fire path at runtime. Rebasing #592 onto main brings that guard in. What's still missing is a **behavioral test** that proves the property by exercising the code path, not by grepping text.

## Task
1. Rebase onto `origin/main` (above) so the #596 runtime guard is present on this branch.
2. Add a **behavioral** test (not a text/grep assertion) that mechanically proves the AutoReview self-fire path can NEVER emit `event=APPROVE`:
   - Drive the actual self-fire review function/codepath with a scenario that would (naively) approve, and assert it **refuses / raises / downgrades** rather than POSTing `event=APPROVE`.
   - Assert the only review events the path can emit are `COMMENT` / `REQUEST_CHANGES`.
   - Cover the raw `gh api -X POST .../reviews` route specifically (that's the gap #596 closed) — assert the guard rejects an APPROVE there.
3. Keep the change scoped to the test + any minimal wiring needed to make the guard unit-testable. Do not broaden the AutoReview feature surface.

## Allowed paths (nothing else)
`validators/tests/**`, the AutoReview self-fire module(s) already in this PR's diff (only if a tiny seam is needed to make the guard testable), `.ce/changelog/**`, `.ce/pr-manifests/**`.

## Evidence (DoD)
- Full `ce validate-pr` GREEN (CI-parity, full suite). The new behavioral test PASSES and, if you temporarily remove the #596 guard locally, it FAILS (prove it actually catches the violation — then restore the guard).
- ⚠️ **G5 BODY FORMAT (mandatory):** the PR body MUST contain exactly ONE line formatted precisely as `- **Declared work class:** <tiny|story|feature|epic>` (a `**Work class:**` header or a `[PASS]` log line does NOT match). Pick the tier the gate derives.

## Stop-line
- Green + self-push works → push to `ce-292-autoreview` (updates PR #592) + comment "rebased onto main (#596 guard) + behavioral never-APPROVE test added" referencing ce-ops#292. Do NOT approve / merge / enqueue — the controller re-reviews and holds the gate.
- Green but push FAILS (self-push gap #337 fallback) → STOP + report `READY-FOR-HARVEST: branch ce-292-autoreview, <N> commits, preflight green`.
- Note: if your container's libsodium gap fails `check-examples` on an unrelated fixture and that is your ONLY failure, it is pre-existing — say so and proceed.
- Preflight RED on a NEW gate from your change → STOP + report the failing gate.
