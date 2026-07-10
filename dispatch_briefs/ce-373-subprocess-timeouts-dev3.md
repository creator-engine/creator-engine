# SEED BRIEF — ce-ops#373: bound validate-pr subprocess network calls with timeouts — SEAT: dev-3

**Context (self-contained):** `ce validate-pr` makes subprocess/network calls (git fetch, gh API, live-base resolution) that can HANG indefinitely if the network stalls — no-hang policy violation. Bound every network-touching subprocess call with a sane timeout so validate-pr fails fast with an actionable message instead of hanging (critical for unattended/conveyor runs).

**Branch:** `ce-373-subprocess-timeouts` (off `origin/main`). **Role:** implementer. **Work class:** by floor.
**Repo:** creator-engine/creator-engine. Contained VPS seat: worktree `/var/tmp`, branch off origin/main (fetch first), READY-FOR-HARVEST when done.

## Goal
Add explicit `timeout=` (or equivalent) to all network-touching subprocess invocations in the validate-pr path, with fail-fast + actionable error on timeout (which call, what to check), never a silent hang. Keep a single sane default (configurable via constant/env), applied consistently.

## Scope — exactly these (you OWN pr_preflight subprocess calls; a parallel lane #382 owns ce_brain_drift.py — do NOT touch it)
- `validators/creator_engine_validator/pr_preflight.py` — its subprocess/network runners (git fetch, live-base resolve, gh). Wrap with timeouts + fail-fast.
- `validators/creator_engine_validator/onboard_apply_live.py` — same, its network subprocess calls.
- Their tests under `validators/tests/` — add: a timeout is passed to each network call; a simulated-timeout surfaces an actionable error (not a hang, not a bare traceback); non-network local calls are unaffected.
- `.ce/pr-manifests/ce-373-subprocess-timeouts.md` + `.ce/changelog/ce-373-subprocess-timeouts.md`
Do NOT touch ce_brain_drift.py, the workflow, or anything else. Code diff with tests → test-coupling satisfied.

## Constraints
- Don't change WHAT the calls do, only bound them + fail fast on timeout.
- Use monkeypatch/fakes for the timeout tests (no real network in tests).

## Evidence / DoD
- Owned gates + targeted tests GREEN in-container; controller runs full validate-pr on DGX host venv (PYTHONPATH=validators) at harvest.
- Show the simulated-timeout → actionable-error test in your report.
- Carrier stem == branch slug; regen after final commit; `rm -rf validators/build` before `git add`.
- `git commit && echo <SHA>`; READY-FOR-HARVEST. Do NOT push/approve/merge.
