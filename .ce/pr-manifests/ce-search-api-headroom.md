# PR path manifest — Search API headroom for parallel pollers

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs `verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-search-api-headroom` and requires this PR's `origin/main..HEAD` diff to equal exactly the authorized path-set below (the carrier lists itself).

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=16

AUTHORIZED_PATHS_SHA256=9921fc261a8e559d548cdb694b52f0f7c79515b35c4e762279f60f440ecb8acc

```text
.ce/changelog/ce-search-api-headroom.md
.ce/pr-manifests/ce-search-api-headroom.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/forge/eviction_detection.py
validators/creator_engine_validator/forge/integrator_belt.py
validators/creator_engine_validator/forge/integrator_runner.py
validators/creator_engine_validator/forge/review_pickup.py
validators/creator_engine_validator/forge/search_rate_limiter.py
validators/creator_engine_validator/pickup.py
validators/creator_engine_validator/pickup_search.py
validators/creator_engine_validator/search_rate_limiter.py
validators/tests/unit/test_eviction_detection.py
validators/tests/unit/test_integrator_belt.py
validators/tests/unit/test_review_pickup.py
validators/tests/unit/test_search_rate_limiter.py
validators/tests/unit/test_version_boundary.py
```
