# PR path manifest - ceops95-seat-lifecycle-phase1

Design/task: `creator-engine/ce-ops#95` Phase 1, ratified by Operator.

Base:
`3e6b516dd35e6a4350696a70dc90cb48369cfc97`

This is the closed path set for Phase 1 only. It intentionally excludes
`ce seats ls`, sampling/read-model commands, cockpit changes, reaper
integration, and backlog reaper code.

Per-file purpose:

- **`.ce/changelog/ceops95-seat-lifecycle-phase1.md`** *(A)* - per-change changelog fragment.
- **`.ce/pr-path-manifest.md`** *(A)* - this closed path-set manifest.
- **`schemas/seat-lifecycle.schema.yaml`** *(A)* - schema for the spawn-time lifecycle object.
- **`validators/creator_engine_validator/seat_lifecycle.py`** *(A)* - shared atomic writer/reader, NDJSON audit, escalation, policy constants, and probe seams.
- **`validators/creator_engine_validator/launch_runtime.py`** *(M)* - `ce launch` registration after spawn/resource-confirm plus additive `LaunchResult` refs.
- **`validators/creator_engine_validator/lane_runtime.py`** *(M)* - `ce lane launch` registration after pane registry write plus additive result refs.
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* - CLI lifecycle metadata and work-claim binding plumbing.
- **`validators/tests/unit/test_launch_runtime.py`** *(M)* - dry-run purity, launch registration, and registration-failure warning/escalation tests.
- **`validators/tests/unit/test_lane_runtime.py`** *(M)* - lane pane-registry plus lifecycle registration test.
- **`validators/tests/unit/test_ce_launch_cli.py`** *(M)* - `--claim-ticket` binding persistence test.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* - rebuilt app wheel for source parity.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - refreshed digest for the rebuilt app wheel.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=12

AUTHORIZED_PATHS_SHA256=9bfcfb335632e35944e4e17f2101274e52624c19ba2ef99b4b44710500d31670

```text
.ce/changelog/ceops95-seat-lifecycle-phase1.md
.ce/pr-path-manifest.md
schemas/seat-lifecycle.schema.yaml
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/lane_runtime.py
validators/creator_engine_validator/launch_runtime.py
validators/creator_engine_validator/seat_lifecycle.py
validators/tests/unit/test_ce_launch_cli.py
validators/tests/unit/test_lane_runtime.py
validators/tests/unit/test_launch_runtime.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
