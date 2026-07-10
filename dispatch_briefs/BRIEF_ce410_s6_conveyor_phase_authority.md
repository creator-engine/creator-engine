# DISPATCH BRIEF — CE-410 slice 6: ce410-conveyor-phase-authority (dev-4)

- **Ticket:** ce-ops#410 (REOPENED — plain mention only, NO `Closes`), slice 6 of 10 (Track A).
- **Branch:** `ce-410-conveyor-phase-authority` off freshly fetched `origin/main`
  (git fetch origin main first; fetch failure = report BLOCKED).
- **Worktree:** `/var/tmp/wt-ce410-s6` (NOT /workspace).
- **Role:** implementer. Task-scoped write only. No approval/merge/gate authority.
- **Declared work class:** story (S/M).
- **Gate-adjacent:** YES → PR flagged for independent non-author review. No gate weakened; armed
  mode keeps REFUSING (arming is downstream, needs all phases + Operator ratification).

## Context (self-contained)
CE-410 blocker 3 (conveyor side), phase-authority typing. Slice 2 (merged, #761) put conveyor
work-item PATHS onto daemon-allocated receipts. This slice types the conveyor RUNNERS by phase so
transport credentials and local-git/validation phases can't share one ambient env. Evidence on
current main (`validators/creator_engine_validator/conveyor.py`):
- `GitRunner` has NO env parameter — `_default_git_runner(args, cwd)` (~469) runs git with the
  daemon's ambient git config/credentials; every conveyor git phase inherits the same environment.
- `_default_validate_runner(...)` (~484) MERGES over `os.environ`:
  `merged_env = None if env is None else {**os.environ, **dict(env)}` (~489) — validation inherits
  GH_TOKEN, wall secrets, SSH agent, credential helpers. (Full credentialless VALIDATION SANDBOX
  is slice 7 — do NOT build the sandbox runner here; this slice is the TYPING + env-parameter seam
  that slice 7 plugs into.)

## Scope (design blocker 3, step 4 — phase-scoped runner typing + GitRunner env param)
1. Give conveyor git execution an explicit env seam: add an `env` parameter to the `GitRunner`
   call path (`_git`, `_fetch_base`, `_carrier_git_runner`, `_default_git_runner`) so git phases
   receive an EXPLICIT env mapping instead of inheriting ambient process env. Default must be a
   SCRUBBED local-git env (GIT_CONFIG_NOSYSTEM=1, GIT_TERMINAL_PROMPT=0, minimal PATH, no GH_*/
   SSH_*/credential-helper vars) — NOT `os.environ`.
2. Introduce phase-scoped runner typing so the armed flow distinguishes transport-authority git
   (fetch/push — may carry transport credentials) from local-git phases (init/config/checkout/
   merge/diff/add/commit — credentialless). If slice 4's `authority_contexts` module has landed
   on main by the time you branch, CONSUME its `TransportCredentialContext`/`LocalGitContext`
   types; if it has NOT landed yet, define the minimal conveyor-local phase enum/typing and leave
   a clear TODO seam to adopt authority_contexts later (check `git log origin/main` for
   `authority_contexts.py` before deciding — do not hard-depend on an unlanded module).
3. Stop `_default_validate_runner` from merging `os.environ`: it must run validation with ONLY an
   explicit allowlisted env (the env passed in), no ambient merge. (The credentialless sandbox
   RUNNER that fully realizes this is slice 7; here you remove the ambient merge and make the env
   explicit/allowlisted — a validator that gets `{PYTHONPATH,TMPDIR}` must receive exactly that,
   not that-plus-os.environ.)
4. Tests: git phases receive the scrubbed explicit env (no GH_TOKEN/SSH_AUTH_SOCK present);
   validation runner receives ONLY the passed env with a sentinel GH_TOKEN in os.environ proven
   ABSENT from what the validator sees; existing conveyor tests + slice-2 receipt/TOCTOU/argv
   regressions still pass (rewrite fixtures that assumed ambient env, don't weaken assertions).

## Allowed paths
- `validators/creator_engine_validator/conveyor.py`
- `validators/creator_engine_validator/conveyor_daemon.py` (only if runner wiring requires it)
- `validators/tests/unit/test_conveyor.py`, `validators/tests/unit/test_conveyor_daemon.py`
- `.ce/changelog/ce-410-conveyor-phase-authority.md` (REQUIRED)
FORBIDDEN: integrator_belt.py, v3_cli.py (slice 4 territory — dev-1 active), daemon_allocation.py
(read-only), release/cli files, any gate surface.
NOTE: the per-PR carrier `.ce/pr-manifests/…` is HARVEST-SIDE — do NOT create it; your preflight
bar is full `ce validate-pr` MINUS the path-manifest-carrier check (the controller harvest adds
the carrier and runs the complete preflight on the staged branch, as with slices 2/3).

## Standing preflight directive (ce-ops#303)
Run FULL `ce validate-pr` GREEN in one pass before commit-for-harvest (the carrier check will be
the only expected miss — see NOTE above). Venv: `.venv/bin/python -m pytest`.

## Evidence + stop line
- Commit, echo `git rev-parse HEAD`. Signal: `READY-FOR-HARVEST ce-410-conveyor-phase-authority <sha>`
- STOP after signal. No push, no PR, no other tickets. Blocked >2 attempts on same failure →
  report BLOCKED + failing output (do not thrash; carrier-only preflight miss is EXPECTED, not a blocker).
