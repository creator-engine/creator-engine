# PR path manifest — ce-ops#218 · Integrator uses latestOpinionatedReviews

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs `verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-integrator-reviews-fix` and requires this PR's `origin/main..HEAD` diff to equal exactly the authorized path-set below (the carrier lists itself).

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=3d702ef0670e0e489e6feded3d14a18ffb5de02ee8838faa986762867d5c7234

```text
.ce/changelog/ce-integrator-reviews-fix.md
.ce/pr-manifests/ce-integrator-reviews-fix.md
validators/creator_engine_validator/forge/integrator_belt.py
validators/tests/unit/test_integrator_belt.py
```
