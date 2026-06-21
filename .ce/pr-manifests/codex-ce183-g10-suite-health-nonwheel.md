# PR path manifest - codex-ce183-g10-suite-health-nonwheel - ce-ops#183 G10 Validator suite health

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref codex/ce183-g10-suite-health-nonwheel
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below, including this carrier.

Base:
`fb26b7dadb67962895c099bd5efd1d8c0cf7e328` (`origin/main` at branch creation).

Change:
ce-ops#183 stabilizes the non-wheel G10 validator full-suite failures
reproduced on clean current main. The fix hardens repo-root discovery against
empty ambient `.git` directories, keeps unauthenticated git-call environments
token-clean under exported `GH_TOKEN`, and moves greenfield onboarding CLI test
workspace roots under pytest tmp paths.

Per-file purpose:
- **`.ce/changelog/ce183-g10-suite-health-nonwheel.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/codex-ce183-g10-suite-health-nonwheel.md`** *(A)* - this carrier.
- **`validators/creator_engine_validator/git_worktree.py`** *(A)* - shared real git worktree root detector.
- **`validators/creator_engine_validator/ce_event_runtime.py`** *(M)* - use robust repo-root auto-detection for CE-event spool ignore checks.
- **`validators/creator_engine_validator/checks/handoff_schema.py`** *(M)* - use robust repo-root detection for schema lookup fallback.
- **`validators/creator_engine_validator/fanin_runtime.py`** *(M)* - use robust repo-root auto-detection for fan-in packet ignore checks.
- **`validators/creator_engine_validator/forge/change_push.py`** *(M)* - scrub ambient GitHub token env vars from local unauthenticated git calls.
- **`validators/creator_engine_validator/forge/credential_runner.py`** *(M)* - scrub ambient `GH_TOKEN` before setting the explicit scoped token.
- **`validators/creator_engine_validator/integration_queue_dry_run.py`** *(M)* - use robust repo-root auto-detection for preview ignore checks.
- **`validators/creator_engine_validator/pcl_runtime.py`** *(M)* - use robust repo-root auto-detection for PCL cache ignore checks.
- **`validators/creator_engine_validator/transcript_archive.py`** *(M)* - use robust repo-root auto-detection for transcript archive ignore checks.
- **`validators/tests/integration/test_greenfield_first_project.py`** *(M)* - keep plan-only greenfield workspace probes under tmp.
- **`validators/tests/unit/test_git_worktree.py`** *(A)* - regression coverage for empty `.git`, normal checkouts, and worktree `.git` files.
- **`validators/tests/unit/test_handoff_schema.py`** *(M)* - regression coverage for handoff schema scans under an empty ancestor `.git`.
- **`validators/tests/unit/test_v3_cli.py`** *(M)* - tmp-scoped greenfield workspace fixture helper for CLI apply tests.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=15

AUTHORIZED_PATHS_SHA256=d57402ff1c4819bc47091f8a52d6a6049f8375b4ddc0040369654969c506ff50

```text
.ce/changelog/ce183-g10-suite-health-nonwheel.md
.ce/pr-manifests/codex-ce183-g10-suite-health-nonwheel.md
validators/creator_engine_validator/ce_event_runtime.py
validators/creator_engine_validator/checks/handoff_schema.py
validators/creator_engine_validator/fanin_runtime.py
validators/creator_engine_validator/forge/change_push.py
validators/creator_engine_validator/forge/credential_runner.py
validators/creator_engine_validator/git_worktree.py
validators/creator_engine_validator/integration_queue_dry_run.py
validators/creator_engine_validator/pcl_runtime.py
validators/creator_engine_validator/transcript_archive.py
validators/tests/integration/test_greenfield_first_project.py
validators/tests/unit/test_git_worktree.py
validators/tests/unit/test_handoff_schema.py
validators/tests/unit/test_v3_cli.py
```
