# DISPATCH BRIEF — CE-410 slice 3: ce410-integrator-alloc-wire (dev-3)

- **Ticket:** ce-ops#410 (conveyor arming fix), slice 3 of 10 (Track B, integrator).
- **Branch:** `ce-410-integrator-alloc-wire` — branch off **freshly fetched** `origin/main`
  (run `git fetch origin main` first; if fetch fails, report BLOCKED — do not build on stale main).
- **Worktree:** create under `/var/tmp/wt-ce410-s3` (NOT /workspace).
- **Role:** implementer. Task-scoped write authority only. No approval/merge/gate authority.
- **Declared work class:** story (M-class, target ≤ ~400 LOC diff).

## Context (self-contained — do not fetch external tickets)
CE-410 blocker 1 (integrator side): `LiveGitHubRepairAdapter` allocates predictable scratch paths
from a caller-provided root — `self.work_root = Path(work_root)` (integrator_belt.py ~2036-2053);
`_prepare_workspace()` uses `work_root / repo_slug / pr-number-head-prefix`, **deletes an existing
path with rmtree, then recreates it** (~2171-2176). The CLI exposes the root directly as
`--work-root` defaulting to `.ce/integrator-belt` (v3_cli.py ~4488-4490, passed in at ~4715-4719).
Predictable caller-controlled paths + rmtree = the arming blocker.

Slice 1 already landed on main (PR #758): module
`validators/creator_engine_validator/forge/daemon_allocation.py` provides
`DaemonRuntimeRoots`, `DaemonPathAllocation`, `DaemonPathReceipt`, `DaemonPathAllocator` with
`allocate_integrator_workspace(...)`, `verify_receipt(...)`, `cleanup(...)`. Root mode-checks
(daemon-owned, not group/world-writable, no symlinked/relative roots), HMAC-per-instance receipts,
mkdtemp-style randomized dirs. **REUSE this module — do not reimplement any part of it.**

## Scope (from the ratified CE-410 design, blocker 1 / integrator)
1. Replace `_prepare_workspace()` deterministic path construction with
   `allocator.allocate_integrator_workspace(repo, pr_number, head_sha)` — fresh randomized dir
   under the daemon-private root, carrying a receipt.
2. Remove the `shutil.rmtree()` of predictable paths. Cleanup/GC happens ONLY through
   `allocator.cleanup(receipt)` — allocator-owned allocations under the private root, by receipt.
3. CLI: replace `--work-root` with `--runtime-root` that is validated as daemon-private via
   `DaemonRuntimeRoots.from_root(...)` (refuse relative, symlinked-through-untrusted, broad, or
   non-0700/non-daemon-owned roots — the module already does these checks; wire them in and fail
   closed). For `--work-root`: keep the flag recognized but make it a hard fail-closed error
   pointing to `--runtime-root` (no silent alias) — visible deprecation, no behavior fallback.
4. `LiveGitHubRepairAdapter.__init__` takes the allocator (or `DaemonRuntimeRoots`) instead of a
   raw `work_root` Path; two allocations for the same PR/head must yield different directories,
   both receipted.
5. Emit secret-free audit records per allocation/cleanup (allocation_id, root kind, relative
   paths, cleanup result). Expose allocation id in logs for diagnosis (replaces the debugging
   value of predictable paths).

## Explicit NON-scope (later slices — do NOT do these now)
- No env/credential handling changes (`git_env_with_token`, `gh_runner_with_token`,
  transport/local context split) — that is slices 4-5.
- No validation-sandbox work — slices 7-8.
- Do NOT touch `conveyor.py` / `conveyor_daemon.py` (slice 2 is in flight on another seat).

## Allowed paths (touch NOTHING else)
- `validators/creator_engine_validator/forge/integrator_belt.py`
- `validators/creator_engine_validator/v3_cli.py` (only the queue-poll/--runtime-root wiring)
- `validators/tests/unit/test_integrator_belt.py` (+ the v3_cli test file that covers queue-poll
  flags, if one exists)
- `.ce/changelog/ce-410-integrator-alloc-wire.md` (REQUIRED changelog fragment)

**FORBIDDEN:** `conveyor.py`, `conveyor_daemon.py`, `daemon_allocation.py` (read-only consumer),
`cli.py`, `release_bump.py`, `release_orchestrate.py` (another seat's territory), any gate or
authority surface.

## Test plan (from design)
- Adapter no longer deletes a predictable path; two allocations for same PR/head create different
  directories and both carry receipts.
- Relative/symlinked/world-writable/group-writable `--runtime-root` refused fail-closed.
- `--work-root` now errors with actionable message naming `--runtime-root`.
- Cleanup only via receipt; foreign/forged receipt refused.
- Regression: existing integrator_belt tests pass (rewrite fixtures that relied on `work_root`
  to use a real allocator over a tmp runtime root).

## Standing preflight directive (ce-ops#303)
Run the FULL local validator preflight (`ce validate-pr`, CI-parity) GREEN in one pass before
commit-for-harvest; do not discover gates via CI. Venv has no activate — use
`.venv/bin/python -m pytest` / repo tooling as-is.

## Evidence + stop line
- Commit on the branch, then report: `git rev-parse HEAD` — echo the SHA. A done-report without a
  verifiable commit SHA is NOT done.
- Signal exactly: `READY-FOR-HARVEST ce-410-integrator-alloc-wire <sha>`
- STOP after the signal. Do NOT push (controller harvests), do NOT open a PR, do NOT touch any
  other ticket. If blocked >2 attempts on the same failure, report BLOCKED with the failing
  output instead of thrashing.
