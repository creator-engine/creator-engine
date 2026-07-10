# DISPATCH BRIEF — CE-410 slice 2: ce410-conveyor-alloc-wire (dev-4)

- **Ticket:** ce-ops#410 (conveyor arming fix), slice 2 of 10 (Track A).
- **Branch:** `ce-410-conveyor-alloc-wire` — branch off **freshly fetched** `origin/main`
  (run `git fetch origin main` first; if fetch fails, report BLOCKED — do not build on stale main).
- **Worktree:** create under `/var/tmp/wt-ce410-s2` (NOT /workspace).
- **Role:** implementer. Task-scoped write authority only. No approval/merge/gate authority.
- **Declared work class:** story (M-class, target ≤ ~400 LOC diff).
- **Gate-adjacent:** YES — this PR will be flagged for independent non-author review. Do not
  weaken any existing gate. Armed mode must keep REFUSING throughout (arming needs all 4 CE-410
  phases + Operator ratification — far downstream of this slice).

## Context (self-contained — do not fetch external tickets)
CE-410 blocker 1 (conveyor side): `ConveyorDaemonItem` carries executable path fields
(`worktree_path`, `bundle_path`, `repo_path`) whose provenance is a **default-True boolean**
`daemon_owned_paths_allocated` (conveyor_daemon.py ~lines 105-130). `_process_armed()` checks only
that boolean (~409-416). Any caller constructing the item directly can self-mark as daemon-owned.

Slice 1 already landed on main (PR #758): module
`validators/creator_engine_validator/forge/daemon_allocation.py` provides
`DaemonRuntimeRoots`, `DaemonPathAllocation`, `DaemonPathReceipt`, `DaemonPathAllocator` with
`allocate_conveyor_paths(...)`, `verify_receipt(...)`, `cleanup(...)`. HMAC-per-instance receipts,
constant-time comparison, symlink/`..` confinement re-checked at verify time, forgery +
cross-instance rejection tests. **REUSE this module — do not reimplement any part of it.**

Also landed (PR #759): argv/ref hardening in the same conveyor files (`--` terminators,
`_reject_git_ref_shape` on all five ref slots). Your base includes it; preserve it.

## Scope (from the ratified CE-410 design, blocker 1 / conveyor)
1. Replace `daemon_owned_paths_allocated: bool` with an allocation-receipt check:
   - `ConveyorDaemonItem.from_mapping()` stays data-only: returns an item with NO executable
     paths and NO receipt.
   - In armed flow, before `prepare_runner`, `_process_armed()` asks a `DaemonPathAllocator`
     (injected seam, like the existing runner seams) to `allocate_conveyor_paths(...)` fresh for
     the item; allocated paths — not payload placeholders — flow into prepare/land/push/pr.
   - `_process_armed()` REFUSES any item that has executable paths but no receipt valid for the
     current allocator instance (`verify_receipt`).
   - REMOVE the default-true provenance bit entirely. Direct `ConveyorDaemonItem` path use must
     require an explicit `allocation_receipt`.
2. Keep existing path confinement (`_path_confinement_violations`, `_confine_path`) as
   defense-in-depth secondary assertion — confinement alone no longer proves provenance.
3. Emit a secret-free audit record per allocation (allocation_id, item key, root kind, relative
   paths, mode-check + cleanup results). Never log the nonce/HMAC secret.
4. Armed `ConveyorDaemon` construction refuses if no allocator is injected (same fail-closed
   pattern as the existing missing-seams refusal at ~310-327).

## Allowed paths (touch NOTHING else)
- `validators/creator_engine_validator/conveyor_daemon.py`
- `validators/creator_engine_validator/conveyor.py` (only if the runner seam signature requires it)
- `validators/tests/unit/test_conveyor_daemon.py`, `validators/tests/unit/test_conveyor.py`
- `.ce/changelog/ce-410-conveyor-alloc-wire.md` (REQUIRED changelog fragment)

**FORBIDDEN:** `integrator_belt.py`, `v3_cli.py`, `daemon_allocation.py` (read-only consumer),
anything under queue-daemon/approval-wall, any gate or authority surface.

## Test plan (from design)
- Direct `ConveyorDaemonItem` with paths and no receipt fails before prepare/land/git/gh.
- Data-only discovery → allocator called exactly once in armed mode; allocated paths flow downstream.
- Forged receipt from another allocator instance is refused.
- Regression: existing payload control-field rejection, path confinement, TOCTOU, and #759 argv/ref
  tests remain passing (rewrite fixtures to use allocator-issued paths where they relied on the bool).

## Standing preflight directive (ce-ops#303)
Run the FULL local validator preflight (`ce validate-pr`, CI-parity) GREEN in one pass before
commit-for-harvest; do not discover gates via CI. Venv has no activate — use
`.venv/bin/python -m pytest` / repo tooling as-is.

## Evidence + stop line
- Commit on the branch, then report: `git rev-parse HEAD` — echo the SHA. A done-report without a
  verifiable commit SHA is NOT done.
- Signal exactly: `READY-FOR-HARVEST ce-410-conveyor-alloc-wire <sha>`
- STOP after the signal. Do NOT push (you have no push lane — controller harvests), do NOT open a
  PR, do NOT touch any other ticket. If blocked >2 attempts on the same failure, report BLOCKED
  with the failing output instead of thrashing.
