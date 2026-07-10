# DISPATCH BRIEF — CE-410 slice 4: ce410-authority-contexts-core (dev-1)

- **Ticket:** ce-ops#410 (REOPENED — reference as plain mention only, NO `Closes` syntax), slice 4 of 10 (Track B).
- **Branch:** `ce-410-authority-contexts-core` off freshly fetched `origin/main`.
- **Worktree:** fresh worktree under ~/.cache/ (your convention) — NOT your main checkout.
- **Role:** implementer. No approval/merge/enqueue authority; you MAY self-push the branch and open
  the PR (your self-push lane) after FULL `ce validate-pr` GREEN in one pass.
- **Declared work class:** story (S/M; if the honest final diff crosses the G5 floor, escalate the
  declared class and SAY SO in the PR body rather than trimming tests).

## Context (self-contained)
CE-410 blocker 3: one credentialed git/gh environment is shared across transport and local git
phases, and token handling mutates process-global state. Slice 3 (merged, PR #760) already moved
workspace allocation onto `forge/daemon_allocation.py` receipts. This slice introduces the TYPED
AUTHORITY CONTEXTS and removes process-global token mutation. Evidence on current main:
- `gh_runner_with_token()` temporarily writes GH_TOKEN into process-global `os.environ`
  (integrator_belt.py ~505-519) — unsafe around any subprocess/thread boundary.
- `git_env_with_token()` copies ALL of os.environ and adds GH_TOKEN (~522-525).
- `LiveGitHubRepairAdapter` stores `dict(git_env or os.environ)` and `_git()` passes that env to
  EVERY git subprocess — fetch/push need transport credentials; init/config/checkout/merge/diff/
  add/commit do not (~2036-2060, _git call sites).

## Scope (design blocker 3, steps 1-2 ONLY — phase-split of fetch/push vs local commands is
slice 5, do NOT do it here beyond what the context types require)
1. New module `validators/creator_engine_validator/forge/authority_contexts.py` with three typed
   context value objects:
   - `TransportCredentialContext` — source-host reads/writes only (gh, git fetch/push, PR create).
     Carries a token provider / explicit env mapping; never passed to validation.
   - `LocalGitContext` — credentialless local git env: scrubbed, `GIT_CONFIG_NOSYSTEM=1`,
     `GIT_TERMINAL_PROMPT=0`, sandbox-private HOME/XDG_CONFIG_HOME, `core.hooksPath=/dev/null`
     posture; no GH_*/GITHUB_*/SSH_*/GIT_ASKPASS/credential-helper vars.
   - `ValidationSandboxContext` — verification role, no credentials, no egress by default
     (a value object now; the runner that consumes it is slice 7).
   Make the three types mechanically non-interchangeable (distinct classes, no shared base that
   allows substitution; consuming signatures take the specific type).
2. Replace process-global token mutation: add `EnvGhRunner` (or equivalent) that passes an
   explicit env to subprocess.run — `gh_runner_with_token()` must no longer write to os.environ
   (keep the old callable only as a deprecated test-compat shim if existing tests require it, and
   mark it clearly).
3. Wire `integrator_belt.py` construction sites (`make_live_action_runner`, queue-poll wiring in
   v3_cli.py) to BUILD the typed contexts from the token instead of raw env dicts — internal
   plumbing may still consume `.env` mappings from the contexts, but no call site constructs a
   combined ambient env itself anymore.
4. Tests: sentinel test proving no process-global GH_TOKEN mutation (concurrent observer sees no
   change); contexts refuse credential-bearing keys in LocalGitContext/ValidationSandboxContext
   construction; type-confusion attempts fail at the signature/type level; existing integrator
   tests keep passing.

## Allowed paths
- `validators/creator_engine_validator/forge/authority_contexts.py` (new)
- `validators/creator_engine_validator/forge/integrator_belt.py`
- `validators/creator_engine_validator/v3_cli.py` (queue-poll construction only)
- `validators/tests/unit/test_authority_contexts.py` (new), `validators/tests/unit/test_integrator_belt.py`
- `.ce/changelog/ce-410-authority-contexts-core.md` (REQUIRED)
- `.ce/pr-manifests/ce-410-authority-contexts-core.md` (regen via carrier_gen.write_carriers(base=<merge-base>) — you self-push, so the carrier is yours to add; never hand-edit)
FORBIDDEN: conveyor.py, conveyor_daemon.py, daemon_allocation.py (read-only), release/cli.py files.

## Evidence + stop line
- FULL `ce validate-pr` GREEN one pass → push → open PR. Body: exactly one
  `- **Declared work class:** <class>` line; mention ce-ops#410 plainly (NO Closes); note
  credential-handling slice → flag for independent non-author review.
- Report: `PR-OPENED <number> <head-sha>` in your pane.
- Do NOT approve/merge/enqueue. Blocked >2 attempts on same failure → report BLOCKED + output.
