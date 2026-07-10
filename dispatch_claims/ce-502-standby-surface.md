# WORK CLAIM — ce-502-standby-surface

- seat: dev-1 (self-push lane, VPS host, non-contained)
- dispatched: 2026-07-09 by CE-DEV-2 controller
- brief: .ce/briefs/BRIEF_dev1_restock_batch_20260709.md (unit U2)
- ticket: ce-ops#502
- branch: ce-502-standby-surface
- worktree: ~/creator-engine-ce-502-standby-surface (off origin/main @ add00a60e)
- work class: S

## Claimed paths

- deploy/dgx-controller-runsc/provision-standby-surface.sh (new)
- tools/mint-forge-token.py (new)
- validators/creator_engine_validator/continuity_drill_runtime.py (existing, modify — add standby_liveness gate)
- validators/tests/unit/test_continuity_drill_cli.py (existing, modify — new standby_liveness test cases)
- .ce/changelog/ce-502-standby-surface.md (new)
- .ce/pr-manifests/ce-502-standby-surface.md (new)
- .ce/wt-ce502/READY or .ce/wt-ce502/BLOCKED (signal)

## Scope summary

Three slices:
(A) deploy/dgx-controller-runsc/provision-standby-surface.sh: idempotent bash script that
    provisions the DGX standby controller with a dedicated main-tracking git worktree at
    /home/cedev2/ce-standby-main, verifies `ce takeover --dry-run --json` returns
    ring0_verify.ok=true + initial_state=AWAITING-OPERATOR, and verifies
    mint-forge-token.py runs without traceback.
(B) tools/mint-forge-token.py: standalone helper that mints/passes a forge token for the
    standby; replaces the traceback-producing prior version with guarded imports, --help,
    --dry-run flag, clear error messages. Eliminates D6 Drill #1 secondary failure.
(C) continuity_drill_runtime.py: add standby_liveness field to drill result; drills without
    a standby liveness proof degrade to WARNING rather than silently passing green. Update
    test_continuity_drill_cli.py with new standby_liveness test cases.

## Explicit exclusions

- .ce/brain/assertions.yaml (PR #918 exclusive — BRAIN-LEDGER-BUSY)
- deploy/vps-runsc/run-vps-runsc.sh (PR #918)
- deploy/dgx-runsc/run-codex-runsc.sh (PR #918)
- validators/creator_engine_validator/ce_cli.py (PR #918)
- validators/creator_engine_validator/_versions.py (continuity_drill_runtime already in V1_RUNTIME; no new module added)
- deploy/daemons/smoke-daemon-container.sh (dev-4 in-flight)
- validators/tests/integration/test_release_finalize_integration.py (dev-3 in-flight)

## Signal expected

PR <number> ce-502-standby-surface (non-draft, ready-for-review)
