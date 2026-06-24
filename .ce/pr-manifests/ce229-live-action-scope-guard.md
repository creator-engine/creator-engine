# PR path manifest — 229 · live-action GitHub query must declare scope or fail closed

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs `verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce229-live-action-scope-guard` and requires this PR's `origin/main..HEAD` diff to equal exactly the authorized path-set below (the carrier lists itself).

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=b62c132eb0bc0acd7acb04ae21007839d58456df6d5c73f32801865f622eff34

```text
.ce/pr-manifests/ce229-live-action-scope-guard.md
validators/creator_engine_validator/forge/eviction_detection.py
validators/creator_engine_validator/forge/review_pickup.py
validators/creator_engine_validator/pickup.py
validators/creator_engine_validator/pickup_search.py
validators/tests/unit/test_eviction_detection.py
validators/tests/unit/test_pickup.py
validators/tests/unit/test_review_pickup.py
```
