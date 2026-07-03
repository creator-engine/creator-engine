# PR path manifest — ce-ops#410 · slice 2: conveyor daemon allocation receipts (armed-path provenance)

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-410-conveyor-alloc-wire` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=1530b40883d7ed9e704e21e4fda37843a518ef6070698bd9c35ea75986cb8ad6

```text
.ce/changelog/ce-410-conveyor-alloc-wire.md
.ce/pr-manifests/ce-410-conveyor-alloc-wire.md
validators/creator_engine_validator/conveyor_daemon.py
validators/tests/unit/test_conveyor_daemon.py
```
