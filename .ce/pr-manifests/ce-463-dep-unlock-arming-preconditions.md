# PR path manifest — ce-ops#463 · Arm dependency-unlock LIVE preconditions

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-463-dep-unlock-arming-preconditions` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=512908b7ddffb00abfcff1720a9a13e35a7f0b0fc818c6430e7b0983c9145404

```text
.ce/changelog/ce-463-dep-unlock-arming-preconditions.md
.ce/pr-manifests/ce-463-dep-unlock-arming-preconditions.md
.github/workflows/ce-dependency-unlock.yml
validators/creator_engine_validator/dependency_unlock.py
validators/tests/unit/test_dependency_unlock.py
```
