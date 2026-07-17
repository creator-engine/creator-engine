# PR path manifest — ce-ops#497 · Persist fail-closed conveyor handled-signal receipts
This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-497-signal-receipt-ledger-main5d85` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.
Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.
- **Declared work class:** story
AUTHORIZED_PATHS_COUNT=8
AUTHORIZED_PATHS_SHA256=3c8bb9634e95010e4b6d28cf3ea7cc0050b79a993bffe3e9bc4af46debc3e642
```text
.ce/changelog/ce-497-signal-receipt-ledger-main5d85.md
.ce/pr-manifests/ce-497-signal-receipt-ledger-main5d85.md
validators/creator_engine_validator/conveyor_daemon.py
validators/creator_engine_validator/conveyor_daemon_runner.py
validators/creator_engine_validator/conveyor_discovery.py
validators/tests/unit/test_conveyor_daemon.py
validators/tests/unit/test_conveyor_daemon_runner.py
validators/tests/unit/test_conveyor_discovery.py
```
