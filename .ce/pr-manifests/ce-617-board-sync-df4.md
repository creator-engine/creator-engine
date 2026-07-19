# PR path manifest — ce-ops#617 · org project board sync slice

This per-PR carrier lists the closed authorized path set for the `M` slice.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** M

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=78969ebf10988dab716aed00175ef28ef611b58b95d6e07f32741b55304ed936

```text
.ce/board/board-state.yaml
.ce/changelog/ce-617-board-sync-df4.md
.ce/pr-manifests/ce-617-board-sync-df4.md
.ce/reference/cli.generated.md
docs/reference/cli.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/forge/board_sync.py
validators/tests/unit/test_board_sync.py
validators/tests/unit/test_v1_docs_reconciliation.py
```
