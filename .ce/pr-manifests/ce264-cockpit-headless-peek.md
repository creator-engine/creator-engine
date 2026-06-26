# PR path manifest — ce-ops#264 · cockpit headless-pane peek

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce264-cockpit-headless-peek` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=a6cf084e2596ffc6837542614276923cb644d8294a60bec0f0b515ca28a45f3f

```text
.ce/changelog/ce264-cockpit-headless-peek.md
.ce/pr-manifests/ce264-cockpit-headless-peek.md
validators/creator_engine_validator/runner/cockpit_readmodel.py
validators/creator_engine_validator/v3_cockpit.py
validators/tests/unit/test_cockpit_peek.py
```
