# SEED BRIEF — N1 Conveyor GO-LIVE (daemon-loop + arming) — SEAT: dev-4

**Context (self-contained):** The conveyor library shipped (`validators/creator_engine_validator/conveyor.py`: `prepare_harvest()` + `land_bundle()` with injected git/validate runners; design in `.ce/design/conveyor-harvest-push.md`). What's NOT built (design-only per the Slice Plan): the **daemon-loop that continuously discovers seat-completed work and drives it through harvest→validate→push→PR**, plus the **arming envelope** and **side-effect ledger**. Build that — it mechanizes what the controller does by hand.

**Branch:** `ce-conveyor-golive` (off `origin/main`). **Role:** implementer. **Work class:** by floor (likely M).
**Repo:** creator-engine/creator-engine. Contained DGX seat: worktree `/var/tmp`, branch off origin/main (fetch first), READY-FOR-HARVEST when done.

## Goal — a governed conveyor daemon runner
Build a `conveyor_daemon` (new module, e.g. `validators/creator_engine_validator/conveyor_daemon.py`) that, in a loop:
1. **Discovers** seat-completed-but-unpushed branches (a pluggable discovery function; for now accept an injected list/runner — do NOT hard-code seat access, keep it testable with fakes like conveyor.py does).
2. For each: calls `prepare_harvest()` → `land_bundle()` (reuse the existing API; do not reimplement).
3. **Arming envelope:** every push/PR-creating action is gated behind an explicit arming flag (default OFF / dry-run). When disarmed, it PLANS and logs the would-be actions without mutating. Mirror the fail-closed pattern already in the codebase (e.g. the automerge kill-switch / broker run-mode).
4. **Side-effect ledger:** emit an append-only ledger record for every armed source-host mutation (push, PR-open) — path, sha, action, timestamp-injected (do NOT call Date.now in library code; accept a clock/`now` param).
5. Fail-open per-item: one branch failing must not abort the loop; log + continue.
6. Does NOT approve/merge/enqueue and does NOT run docker itself (execution stays external); it drives harvest→push→PR only. Merge stays the controller/queue-daemon gate.

## Constraints
- **Pure/testable core** like conveyor.py: inject all runners (git, validate, gh, clock, discovery). NO real network/docker/daemon calls in the module — those come from injected runners. Argless Date.now/random are unavailable — accept params.
- Keep the arming DEFAULT DISARMED (dry-run). Landing this PR does NOT arm anything live; arming is a separate controller step.
- Reuse `prepare_harvest`/`land_bundle`; extend, don't duplicate.

## Scope — exactly these
- `validators/creator_engine_validator/conveyor_daemon.py` (new)
- `validators/tests/unit/test_conveyor_daemon.py` (new — fake runners; cover: dry-run plans-no-mutation, armed path calls land+push, per-item failure isolated, ledger records emitted, idempotent re-discovery)
- optionally extend `conveyor.py` ONLY if a small hook is needed (minimize)
- `.ce/pr-manifests/ce-conveyor-golive.md` + `.ce/changelog/ce-conveyor-golive.md`
Code diff with tests → test-coupling satisfied.

## Evidence / DoD
- Owned gates + targeted tests GREEN in-container; controller runs full validate-pr on DGX host venv (PYTHONPATH=validators) at harvest.
- Show the dry-run-plans-no-mutation test + the armed-path test in your report.
- Carrier stem == branch slug; regen after final commit; `rm -rf validators/build` before `git add`.
- `git commit && echo <SHA>`; READY-FOR-HARVEST. Do NOT push/approve/merge.
