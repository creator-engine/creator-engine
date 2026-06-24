# PR path manifest — ce-ops#188 · belt reviews-pickup — v1/v3 boundary decouple

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs `verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce188-belt-reviews-pickup` and requires this PR's `origin/main..HEAD` diff to equal exactly the authorized path-set below (the carrier lists itself).

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=e8c6ab51c5bc13d3fe19802d6da9c0226f29c593d983ecb4687d03a188c35708

```text
.ce/changelog/ce188-belt-reviews-pickup.md
.ce/pr-manifests/ce188-belt-reviews-pickup.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/forge/review_pickup.py
validators/creator_engine_validator/pickup.py
validators/creator_engine_validator/pickup_search.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_review_pickup.py
validators/tests/unit/test_version_boundary.py
```
