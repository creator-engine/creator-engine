# PR path manifest — ce-ops#205 · belt launch-leg governance contract

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref ce205-belt-launch-leg` and requires
this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this
carrier lists itself.

- **Declared work class:** feature

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=7ad68a7d61d39f9c76fffdd045aa2fab6c86d732f6549c802077816043f14d17

```text
.ce/changelog/ce205-belt-launch-leg.md
.ce/pr-manifests/ce205-belt-launch-leg.md
validators/creator_engine_validator/pickup.py
validators/tests/integration/test_belt_launch_e2e.py
validators/tests/unit/test_pickup.py
```
