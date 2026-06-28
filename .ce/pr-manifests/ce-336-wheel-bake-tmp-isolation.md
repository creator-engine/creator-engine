# PR path manifest — ce-ops#336 · Isolate wheel-bake tmp build root

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-336-wheel-bake-tmp-isolation` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=1c2964d38a1df235fdfb57b098fd866e3bfa482cb0f35a8c5114fdc2d97b87e8

```text
.ce/changelog/ce-336-wheel-bake-tmp-isolation.md
.ce/pr-manifests/ce-336-wheel-bake-tmp-isolation.md
validators/creator_engine_validator/wheel_bake.py
validators/tests/unit/test_wheel_bake.py
```
