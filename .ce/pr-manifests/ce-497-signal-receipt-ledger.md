# PR path manifest — ce-ops#497 · signal receipt ledger

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-497-signal-receipt-ledger` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`. Correction note: this same closed carrier set contains descriptor-relative private receipt persistence hardening and hermetic adversarial coverage; no path authorization was expanded.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=fdf09cbdbe58f6744dc15f261f1376ffe07a824b0761c19e4be4cc699843a10e

```text
.ce/changelog/ce-497-signal-receipt-ledger.md
.ce/pr-manifests/ce-497-signal-receipt-ledger.md
validators/creator_engine_validator/conveyor_daemon.py
validators/creator_engine_validator/conveyor_daemon_runner.py
validators/creator_engine_validator/conveyor_discovery.py
validators/tests/unit/test_conveyor_daemon.py
validators/tests/unit/test_conveyor_daemon_runner.py
validators/tests/unit/test_conveyor_discovery.py
```
