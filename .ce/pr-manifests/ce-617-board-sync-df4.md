# PR path manifest — ce-ops#617 · org project board sync slice

This per-PR carrier lists the closed authorized path set for the `M` slice.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** M

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=7694ab2b6c2561b23791a31ddfab4ea302b6f1a48e5230dbe0979c9776214229

```text
.ce/board/board-state.yaml
.ce/changelog/ce-617-board-sync-df4.md
.ce/pr-manifests/ce-617-board-sync-df4.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/forge/board_sync.py
validators/tests/unit/test_board_sync.py
```
