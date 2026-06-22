# PR path manifest - ce151-stale-review-reconcile

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce151-stale-review-reconcile

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

The change (ce-ops#151, the reviews-automation half of #188): a deterministic
rebase-aware stale-review reconciler. Auto-dismisses a `CHANGES_REQUESTED`
review ONLY when its commit is no longer the head AND a distinct reviewer has
approved the current head (superseded by an independent approval); everything
else is re-request-scoped, never auto-dismissed; live objections on head are
untouched. Pure classifier is zero-I/O + exhaustively unit-tested; GitHub I/O is
behind the injectable `GhRunner`. CLI/belt-poll wiring is a separate slice.

Per-file purpose (the closed path-set - 4 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ce151-stale-review-reconcile.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce151-stale-review-reconcile.md`** *(A)* - this carrier.
- **`validators/creator_engine_validator/_versions.py`** *(M)* - classify
  `forge.re_review` in the v3 forge-adapter family (version_boundary taxonomy).
- **`validators/creator_engine_validator/forge/re_review.py`** *(A)* - the
  reconciler: pure classifier + `list_reviews`/`dismiss_review`/`reconcile_reviews`
  behind `GhRunner`.
- **`validators/tests/unit/test_re_review.py`** *(A)* - 14 unit tests (the #309
  scenario, no-fresh-approval re-request, live-CR-current, latest-per-reviewer,
  fail-closed, dry-run vs apply, GhRunner errors).
- **`validators/tests/unit/test_version_boundary.py`** *(M)* - bump V3_RUNTIME
  count 48->49 for `forge.re_review`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=f6fab666bfd1fa422fbbaad552f08a23a2d241080cdeacefe3df6e552702149d

```text
.ce/changelog/ce151-stale-review-reconcile.md
.ce/pr-manifests/ce151-stale-review-reconcile.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/forge/re_review.py
validators/tests/unit/test_re_review.py
validators/tests/unit/test_version_boundary.py
```
