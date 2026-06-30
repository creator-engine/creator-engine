# PR path manifest - ce-L4 - Launch hydration deterministic fallback

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-l4-launch-hydration-fallback` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=1e3c7b108d4415d415aba6b96baf9387b5866e9ac7e8c0933f265cab62cb730f

```text
.ce/changelog/ce-l4-launch-hydration-fallback.md
.ce/pr-manifests/ce-l4-launch-hydration-fallback.md
validators/creator_engine_validator/launch_runtime.py
validators/tests/unit/test_brain_sqlite_vec.py
validators/tests/unit/test_launch_runtime.py
```
