# PR path manifest — ce583-conveyor-receipt-hardening

This per-PR carrier lists the closed authorized path set for ce-ops#583 slices
10–13. CI requires the `base..HEAD` diff to equal this list; the manifest lists
itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

Base: `c245fa6c3ee334d3284f05b067a8e9f700324f14` (`origin/main` at handoff).

Declared work class: **S**.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=96072df8fedd05f169db7f1c53f0ba1b0560a19667c004c383ff14068f383369

```text
.ce/changelog/ce583-conveyor-receipt-hardening.md
.ce/pr-manifests/ce583-conveyor-receipt-hardening.md
validators/creator_engine_validator/conveyor_daemon.py
validators/creator_engine_validator/conveyor_daemon_runner.py
validators/creator_engine_validator/conveyor_discovery.py
validators/tests/unit/test_conveyor_daemon.py
validators/tests/unit/test_conveyor_daemon_runner.py
validators/tests/unit/test_conveyor_discovery.py
```
