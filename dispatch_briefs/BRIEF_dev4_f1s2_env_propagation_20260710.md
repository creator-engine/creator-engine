# DISPATCH — dev-4 — 2026-07-10 — unit: preflight env propagation (F-1 slice 2) — class S
Role: implementer foreman. Signal: `READY-FOR-HARVEST ce-f1s2-preflight-env-propagation <full-40-hex-sha>`
or `BLOCKED ce-f1s2-preflight-env-propagation <one-line-reason>`.

**START-GATE (serialization against an in-flight PR touching the same file):** do NOT create the
branch or edit anything until `origin/main` contains
`validators/creator_engine_validator/checks/disk_headroom.py`
(check after `git fetch origin main`: `git cat-file -e origin/main:validators/creator_engine_validator/checks/disk_headroom.py && echo GATE-OPEN`).
Poll every ~5 minutes. That file arrives with the F-1 slice-1 merge; starting before it lands
would collide with an open PR on `pr_preflight.py`. While waiting you may READ code and plan.

Branch `ce-f1s2-preflight-env-propagation` off freshly fetched origin/main AT-OR-AFTER the
gate-open commit. Worktree /var/tmp/wt-ce-f1s2-preflight-env-propagation. Standing preflight
directive: run `ce validate-pr --profile contained-seat` if your environment can; else focused
tests + BLOCKED(env) per protocol. PRE-SIGNAL CHECKLIST: focused tests green + confidentiality check:
`python -m pytest validators/tests/unit/test_public_docs_confidentiality.py::test_tracked_text_files_contain_no_new_confidential_or_internal_references -q`

## Context (embedded)

Root cause of four host storage incidents on 2026-07-10: in
`validators/creator_engine_validator/pr_preflight.py`, the `_python_env` helper builds the
environment for inner test-suite subprocesses and DROPS the caller's `TMPDIR` and
`PYTEST_ADDOPTS`. Inner pytest runs therefore default their basetemp onto the host's small
tmpfs `/tmp` and exhaust it under load, no matter what the caller sets. The interim fix is
host-side wrapper env only; this unit is the ratified PRODUCT fix (F-1 slice 2).

Required behavior: `_python_env` (and any sibling env-constructing helpers in the same module
with the same defect) must PROPAGATE `TMPDIR` and `PYTEST_ADDOPTS` from the calling environment
when set — caller values as defaults — while its intentional overrides still win where they are
intentional (PYTHONDONTWRITEBYTECODE, PYTHONPATH construction, token-env-var drops). Verify the
actual current code before assuming the exact drop mechanism; the freshly-merged F-1 slice-1
touched this module, so read the post-merge state.

## Unit

1. After the START-GATE opens: locate every env-constructing helper in `pr_preflight.py`
   (`grep -n "os.environ"`); identify which drop TMPDIR/PYTEST_ADDOPTS.
2. Implement propagation-with-override-precedence as specified above, consistently across
   affected helpers.
3. Unit tests (in the module's existing test file, or a new
   `validators/tests/unit/test_pr_preflight_env.py`):
   (a) caller TMPDIR="/custom/path" appears in the built env;
   (b) caller PYTEST_ADDOPTS="-p no:x" appears in the built env;
   (c) neither set → neither present (no spurious defaults);
   (d) intentional overrides still applied (PYTHONDONTWRITEBYTECODE etc.);
   (e) token env vars still dropped.
4. Run the module's focused tests green:
   `python -m pytest validators/tests/unit -k "preflight" -q`.

## Files (allowed writes)

- `validators/creator_engine_validator/pr_preflight.py`
- `validators/tests/unit/test_pr_preflight_env.py` (or the existing pr_preflight test file)
- `.ce/changelog/ce-f1s2-preflight-env-propagation.md` — changelog fragment
- `.ce/pr-manifests/ce-f1s2-preflight-env-propagation.md` — carrier (slug=branch) with exactly
  `- **Declared work class:** S`

Product lens throughout. Synthetic fixtures for tests. No internal ticket references and no
internal host identifiers in committed content.

## Stop lines

`.github/**`, `deploy/**`, `forge/**`, `checks/**` (read-only), `ce_cli.py`, `v3_cli.py`,
`seat_sentinel.py`, all other in-flight modules, `.ce/brain/assertions.yaml`, brain ledger.
Do not push. Do not sign.

## Signal

After focused tests pass and the confidentiality check is green:

1. Commit all changes on branch `ce-f1s2-preflight-env-propagation`. Commit early and often.
2. Signal: `READY-FOR-HARVEST ce-f1s2-preflight-env-propagation <full-40-hex-sha>`

**In-seat validation note:** use the absolute path `/workspace/creator-engine/.venv/bin/ce` and
`/workspace/creator-engine/.venv/bin/python` — bare `ce` does not resolve correctly in the
contained seat after a relaunch.
