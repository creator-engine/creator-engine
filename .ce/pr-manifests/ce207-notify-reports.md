# PR path manifest - ce207-notify-reports - notify status reports

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce207-notify-reports
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. This carrier lists itself.

Base:
`a83d384db810ca540ae9512fb6c0ddfb9ddb9f1d` (`origin/main` at branch creation).

- **Declared work class:** tiny

What this lands:
- Adds a `status_report` notify event fold that summarizes existing
  `runtime_run_outcome` records and spend-ledger records.
- Reuses the shared run-outcome enum already pinned to
  `runtime-evidence.schema.yaml`, and reuses the spend gate's fleet spend meter.
- Reuses the existing confidential-by-default `shape_payload` path with a
  report allow-list, then emits through the existing desktop/exec/webhook sinks.

Per-file purpose (the closed path-set - 4 paths; carrier self-inclusive):
- **`.ce/changelog/ce207-notify-reports.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce207-notify-reports.md`** *(A)* - this carrier.
- **`validators/creator_engine_validator/runner/notify_feed.py`** *(M)* - the
  report fold, report payload shape, and `run_report_once` composition root.
- **`validators/tests/unit/test_notify_feed.py`** *(M)* - TDD coverage for
  run-outcome + spend folding, periodic/idempotent report emission, and report
  secret redaction.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=a3b024ff5bf3b2ca6cbe271ad2813ef069f4cf7d7bdaa5fa10d6ab4d9fed4a21

```text
.ce/changelog/ce207-notify-reports.md
.ce/pr-manifests/ce207-notify-reports.md
validators/creator_engine_validator/runner/notify_feed.py
validators/tests/unit/test_notify_feed.py
```
