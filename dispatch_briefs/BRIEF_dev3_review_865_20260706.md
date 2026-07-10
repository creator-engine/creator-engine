# BRIEF — dev-3 — review-analysis of PR #865 (dev-4's ce-ops#474: verify honors declared protections:reference). Read-only, verdict-only, safe concurrent.
2026-07-06 ~15:4xZ by CE-DEV-2. Mechanics: `git fetch origin pull/865/head:review-865`, throwaway worktree, baseline STRICTLY `git show <merge-base>:<path>`. Head c83d1d5617035d42f3aaabc75e228eabb936f8dc, class story.

Embedded context (no gh in your container): ce-ops#474 — canary C3 found verify_preserved_checks hard-fails on GitHub-Free private repos (403 on branch-protection API) even when the operator's answers file explicitly declared `github.protections: reference`. Ratified product fix (option 1): when reference is DECLARED, verify accepts the 403, skips forge-enforcement assertions, records `protection_floor: documented-not-enforced` in evidence. Undeclared 403 must stay a hard failure; declared+200 must still run normal assertions.

Controller pre-verified (take as given): declaration-gating is the only entry to the acceptance path; evidence key propagates; three failure-direction tests exist; scope = 2 validator modules + 2 test modules + 2 contract docs + gate artifacts, no pinned files.

Your bars (what wasn't checked):
1. SECURITY DIRECTION: can any input other than the answers-file declaration reach the acceptance path (e.g., a crafted API error body, a non-403 error class, case/whitespace variants of "reference")? The declaration must be the sole key.
2. Evidence honesty: the documented-not-enforced record must be un-spoofable by the tenant side and clearly distinguishable from enforced floors downstream.
3. Contract-doc accuracy vs the actual behavior; product lens (no internal refs).
4. Test substance beyond existence: do the three tests assert the RIGHT things (not just exit codes)?
Emit exactly: `VERDICT-865: APPROVE` or `VERDICT-865: REQUEST_CHANGES` + numbered evidence.
