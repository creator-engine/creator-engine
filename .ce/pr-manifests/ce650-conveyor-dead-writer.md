# PR path manifest — ce650-conveyor-dead-writer

This carrier confines the change to removing the unused ledger-path writer
fallback and retaining the injected hardened writer seam.

Canonicalization: `sha256("\\n".join(sorted(unique_paths)) + "\\n")`.

Base: `dd7225d2a29b8bdaa5d0d1898b43ed20cc5bf6e1` (`origin/main` at handoff).

Declared work class: **S**.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=54099c494cbd0f07a2c54db3d265fb985f3d63b010470a43e322c67210c5a0ba

```text
.ce/changelog/ce650-conveyor-dead-writer.md
.ce/pr-manifests/ce650-conveyor-dead-writer.md
validators/creator_engine_validator/conveyor_daemon.py
validators/tests/unit/test_conveyor_daemon.py
```
