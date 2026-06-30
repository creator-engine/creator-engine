# PR path manifest — ce-conveyor · Conveyor harvest core

- **Declared work class:** story

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-conveyor-harvest-core` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=bb03ccdecc640569671e8e9f3a61e342047aa004a81f266985f60a85beb78337

```text
.ce/changelog/ce-conveyor-harvest-core.md
.ce/design/conveyor-harvest-push.md
.ce/pr-manifests/ce-conveyor-harvest-core.md
validators/creator_engine_validator/conveyor.py
validators/tests/unit/test_conveyor.py
```
