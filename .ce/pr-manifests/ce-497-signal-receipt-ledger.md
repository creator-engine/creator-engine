# PR path manifest — ce-ops#497 · signal receipt ledger

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-497-signal-receipt-ledger` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=28a13784bbb5af67635f55ba6a9c2688785e4a237d346306131fbf40b7f19d5c

```text
.ce/changelog/ce-497-signal-receipt-ledger.md
.ce/pr-manifests/ce-497-signal-receipt-ledger.md
validators/creator_engine_validator/conveyor_daemon.py
validators/creator_engine_validator/conveyor_discovery.py
validators/tests/unit/test_conveyor_daemon.py
validators/tests/unit/test_conveyor_discovery.py
```
