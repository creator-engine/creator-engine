# PR path manifest — ce-ops#564 · Snapshot retention inventory slice 1

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-564-snapshot-retention-inventory-s1` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** feature

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=e66135c7d1a5ee5fbf7b1b3478ac77d47a0f7d3024d1f47db0a9a55ca01f4ae5

```text
.ce/changelog/ce-564-snapshot-retention-inventory-s1.md
.ce/pr-manifests/ce-564-snapshot-retention-inventory-s1.md
.ce/reference/schemas.generated.md
validators/creator_engine_validator/schemas/snapshot-retention-inventory.schema.yaml
validators/creator_engine_validator/snapshot_retention.py
validators/tests/unit/test_snapshot_retention.py
```
