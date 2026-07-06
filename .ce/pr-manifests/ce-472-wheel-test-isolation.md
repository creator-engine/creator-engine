# PR path manifest — ce-ops#472 · wheel determinism test isolation

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-472-wheel-test-isolation` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=2978ad5756049bfaa65ff2d217d09abd33b7fae4d9938616ee611640a3da755a

```text
.ce/changelog/ce-472-wheel-test-isolation.md
.ce/pr-manifests/ce-472-wheel-test-isolation.md
validators/tests/unit/test_wheel_bake.py
```
