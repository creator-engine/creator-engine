# PR path manifest - ce-conveyor-golive

- **Declared work class:** M

N1 Conveyor GO-LIVE slice: daemon-loop core plus arming envelope and mutation ledger.

Per-file purpose:

- **`.ce/changelog/ce-conveyor-golive.md`** *(A)* - changelog fragment for the go-live conveyor daemon slice.
- **`.ce/pr-manifests/ce-conveyor-golive.md`** *(A)* - this PR's closed path-set carrier.
- **`validators/creator_engine_validator/conveyor_daemon.py`** *(A)* - pure/testable conveyor daemon core, disarmed by default, with injected discovery/git/validate/gh/clock/ledger seams.
- **`validators/tests/unit/test_conveyor_daemon.py`** *(A)* - focused unit coverage for dry-run planning, armed execution, fail-open item handling, ledger emission, and idempotent re-discovery.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=c5d5c2e457fa5138339ec95ad7b19bf61e99c1db76fbab48a1a67b0db00caee2

```text
.ce/changelog/ce-conveyor-golive.md
.ce/pr-manifests/ce-conveyor-golive.md
validators/creator_engine_validator/conveyor_daemon.py
validators/tests/unit/test_conveyor_daemon.py
```
