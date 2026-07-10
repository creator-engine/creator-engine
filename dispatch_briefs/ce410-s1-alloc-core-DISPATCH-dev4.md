# DISPATCH BRIEF — ce-ops#410 slice 1 — ce410-alloc-core (daemon path allocator module)

- **Seat:** dev-4 (contained, ce-dgx-codex)
- **Role:** implementer
- **Branch:** `ce-410-alloc-core` (off FRESH `origin/main` — fetch first)
- **Work class:** S — PR body must carry exactly one line: `- **Declared work class:** story`
- **Worktree:** new one under `/var/tmp/wt-ce410-alloc/` (NOT /workspace)

## Context (embedded — you cannot read ce-ops)
ce-ops#410 = conveyor-daemon arming fixes. The ratified design is at
`/var/tmp/CE410_ARMING_FIX_DESIGN.md` (transferred alongside this brief; verify its sha256 =
`d36916652fde6c3dff0779f821418cf830ea7858250585c96c798be587c0147f` before use). The design was
sliced into 10 bounded units; THIS dispatch is slice 1 ONLY:

**ce410-alloc-core** — build the allocator module the later slices wire in:
`DaemonRuntimeRoots`, `DaemonPathAllocation`, `DaemonPathReceipt`, `DaemonPathAllocator` —
unforgeable daemon-issued path allocations replacing caller-asserted booleans. Follow the design
doc's section on the allocation-receipt trust model for exact semantics (allocation issuance,
receipt verification, runtime-root confinement, randomized workspace dirs). NO wiring into
conveyor_daemon.py / conveyor.py / integrator_belt.py — that is slices 2/3, other seats/later.

## Files (allowed — EXHAUSTIVE; all NEW)
- `validators/creator_engine_validator/forge/daemon_allocation.py` (new module)
- `validators/tests/unit/test_daemon_allocation.py` (new tests)
- `.ce/changelog/ce-410-alloc-core.md` (REQUIRED)
- `.ce/pr-manifests/ce-410-alloc-core.md` — regen via `carrier_gen.write_carriers(base=<merge-base>)`
  API after `rm -rf validators/build validators/*.egg-info`; never hand-edit.

If the design mandates a different module location, follow the design — but stay out of every
existing file. Zero edits to existing files (imports get wired in later slices).

## Tests must cover
Allocation issuance/uniqueness (randomized dirs), receipt verification success + forgery rejection
(hand-constructed receipt not issued by the allocator must fail), runtime-root confinement
(allocation outside the root rejected), and idempotence/cleanup semantics per the design.

## Standing preflight directive (ce-ops#303)
FULL `ce validate-pr` (CI-parity) GREEN in ONE pass before commit-for-harvest; do not discover
gates via CI. venv has no activate — `.venv/bin/python -m pytest`.

## STOP LINES
- NO edits to conveyor_daemon.py, conveyor.py, integrator_belt.py, v3_cli.py, forge/automerge_*,
  any workflow, any gate file. New files only.
- NO arming logic, NO flag reads. Pure data-model + allocator mechanics + tests.
- If the design's allocator section depends on something not on main, STOP and report BLOCKED.

## Expected evidence (done-report at /var/tmp/ce410-s1-done-report.md)
- Commit SHA (`git rev-parse HEAD` — no verifiable SHA = not done)
- `ce validate-pr` GREEN tail · test names + pass evidence
- Signal `READY-FOR-HARVEST ce-410-alloc-core <SHA>` when complete.
