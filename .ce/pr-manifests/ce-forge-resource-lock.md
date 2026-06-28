# PR path manifest — ce-ops#34 · Add local forge resource locks

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-forge-resource-lock` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=349fd87f0784b8ce702affee8500ec75072c14b04089cd2c0c631ceffb76a577

```text
.ce/changelog/ce-forge-resource-lock.md
.ce/pr-manifests/ce-forge-resource-lock.md
validators/creator_engine_validator/forge/resource_lock.py
validators/tests/unit/test_resource_lock.py
```
