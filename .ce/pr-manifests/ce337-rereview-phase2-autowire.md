# PR path manifest - ce337-rereview-phase2-autowire

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce337-rereview-phase2-autowire
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Base:
`origin/main` at branch handoff.

- **Declared work class:** story
- **story:** ce-ops#216 Integrator lane Phase-2 re-review live wiring

Scope:
Wire the existing base-only/content-drift classifier into the integrator merge
path so a GitHub `REVIEW_REQUIRED` reset after a proven base-only rebase can
restore the same reviewer's prior approval. Content drift, unprovable classifier
state, and reviewer-identity mismatch remain fail-closed.

Per-file purpose:
- **`.ce/changelog/ce337-rereview-phase2-autowire.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce337-rereview-phase2-autowire.md`** *(A)* - this closed path-set carrier.
- **`validators/creator_engine_validator/forge/re_review.py`** *(M)* - expose review-history helper for stale same-reviewer approvals and authenticated-login read.
- **`validators/creator_engine_validator/v3_forge_join.py`** *(M)* - wire same-reviewer approval restore after proven base-only restamp and before merge-gate reread.
- **`validators/tests/unit/test_v3_forge_join.py`** *(M)* - cover base-only restore, content drift refusal, and classifier-uncertain refusal.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=31ea8e3066e6d1c35d9771e2697c1cc5c6a5b6d8cd3aa0a63f6012d6198590b3

```text
.ce/changelog/ce337-rereview-phase2-autowire.md
.ce/pr-manifests/ce337-rereview-phase2-autowire.md
validators/creator_engine_validator/forge/re_review.py
validators/creator_engine_validator/v3_forge_join.py
validators/tests/unit/test_v3_forge_join.py
```
