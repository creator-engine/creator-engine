# PR path manifest — ce-511-seatwatch-s2-events · seat-watch slice 2 detector events

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the path manifest convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-511-seatwatch-s2-events
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below.

Base:
`6ce9527e1a9da3c578266db42b79625fe86392cd` (`origin/main`, worktree creation base).

Summary:
- **Declared work class:** S
- Adds durable state-root JSONL detector records for `idle-without-signal` and `dispatch-undelivered`.
- Adds `dispatch_undelivered` detection when configured dispatch acknowledgement patterns stay absent for the detector threshold.
- Adds a supervised systemd example with restart-on-failure posture and non-retryable expected exit codes.
- Adds focused unit coverage for detector event emission, durable JSONL records, and the systemd asset.

Per-file purpose (the closed path-set — 6 paths):
- **`.ce/changelog/ce-511-seatwatch-s2-events.md`** *(A)* — changelog fragment.
- **`.ce/pr-manifests/ce-511-seatwatch-s2-events.md`** *(A)* — this carrier.
- **`deploy/seat-watch/ce-seat-watch-supervised.example.service`** *(A)* — supervised example unit for restart posture without live rollout.
- **`validators/creator_engine_validator/seat_watch_daemon.py`** *(M)* — adds `dispatch_undelivered` detector events while preserving existing acknowledgement events.
- **`validators/creator_engine_validator/seat_watch_runner.py`** *(M)* — writes durable detector JSONL records under the daemon state root and exposes supervisor exit-code constants.
- **`validators/tests/unit/test_seat_watch_daemon.py`** *(M)* — focused coverage for detector events, state-root ledger writes, exit codes, and systemd posture.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=66cce4dea86323a1576183d2feea4ef8065cf27344f420bd5967fce265804b84

```text
.ce/changelog/ce-511-seatwatch-s2-events.md
.ce/pr-manifests/ce-511-seatwatch-s2-events.md
deploy/seat-watch/ce-seat-watch-supervised.example.service
validators/creator_engine_validator/seat_watch_daemon.py
validators/creator_engine_validator/seat_watch_runner.py
validators/tests/unit/test_seat_watch_daemon.py
```
