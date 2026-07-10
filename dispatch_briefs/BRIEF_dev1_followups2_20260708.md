# BRIEF — dev-1 — 2026-07-08 — 1 STORY unit: review-findings follow-up batch #2

Role: implementer, self-push lane. Branch `ce-followups2-20260708` off fresh origin/main
(`git fetch origin && git checkout -b ce-followups2-20260708 origin/main`). Full `ce validate-pr`
green locally (TMPDIR=$HOME/tmp, -n 4, serialize suites, clean pytest tmpdirs) → push → PR →
`READY ce-followups2-20260708 <sha> PR#<n>`. If blocked: `BLOCKED ce-followups2-20260708 <reason>`.

⚠️ PR BODY RULE: the body must contain EXACTLY ONE line matching
`- **Declared work class:** <value>` — count matches before pushing; do not let a quoted
manifest or prose duplicate it.

All items below are non-blocking findings from today's reviews of MERGED PRs (#895
singleton-redeploy, #896 seat-ready profile) plus one test-isolation race found during harvest.
No item here touches MAJOR-finding surfaces or requires signing/gating acts.

## Items

I1 — `deploy/dgx-runsc/build-image.sh` (line 51): `python3 "${repo_root}/surfaces/render.py"
--arch arm64 build-args` hardcodes arm64 and breaks on x86_64 hosts with an exec-format-error
(the render.py output is arch-specific; the flag mismatch causes Docker build-arg injection to
pass wrong TARGETARCH). Fix: (a) add `--arch` flag to the script's option-parser (add to the
`usage()` heredoc and the `case "$1"` block alongside `--image` and `--dry-run`), setting a
variable e.g. `render_arch`; (b) default `render_arch` to the host arch via
`"$(dpkg --print-architecture 2>/dev/null || uname -m)"`, normalising `aarch64`→`arm64` and
`x86_64`→`amd64` as needed; (c) substitute `--arch "$render_arch"` at line 51 in place of the
literal `arm64`. Arm64 behavior must remain byte-identical on aarch64 hosts.

I2 — `deploy/singleton-redeploy/smoke-singleton-redeploy.sh` function `main`: the assertion
`assert_grep "Would install" "$tmpdir/dry-run.out"` (line ~71) hard-fails on an already-deployed
host where `redeploy-singleton.sh --dry-run` instead emits "Would leave unchanged systemd unit".
Looking at `dry_run_queue_daemon` in `deploy/singleton-redeploy/redeploy-singleton.sh`, the
install-vs-unchanged branch is conditional. Fix: change the assertion so it accepts EITHER
branch. One approach: replace the single `assert_grep "Would install"` call with a shell test that
greps for either pattern, e.g. using a combined `grep -E "Would install|Would leave unchanged"`.
Also assert `assert_grep "Would reload"` and `assert_grep "Would enable"` (which are printed on
both paths) to retain coverage of the common output lines.

I3 — `deploy/singleton-redeploy/redeploy-singleton.sh`, two findings:

  I3a — function `sed_replacement_escape` (line ~43):
    `printf '%s' "$1" | sed 's/[&#]/\\&/g'`
  Backslash is not escaped; a `\` in a repo-root path would be passed verbatim into the `sed -e`
  replacement expression and corrupt it. Fix: escape backslash first, then `&` and `#`:
    `printf '%s' "$1" | sed 's/\\/\\\\/g; s/[&#]/\\&/g'`
  (or equivalently, add `\\` to the character class as the first alternative). Extend the
  smoke-singleton-redeploy.sh or a separate unit test to assert a value containing a backslash
  is correctly round-tripped through `sed_replacement_escape`.

  I3b — functions `dry_run_queue_daemon` (line ~68) and `install_queue_unit_if_changed`
  (line ~98): each creates a temp file with `tmp="$(mktemp ...)"` and cleans up with
  `rm -f -- "$tmp"` only at the LAST line of the function. Under `set -euo pipefail`, any
  intermediate failure (e.g. `render_queue_unit` fails) exits the function without running the
  final `rm`, leaking the file. Fix: add `trap 'rm -f -- "$tmp"' RETURN` immediately after each
  `mktemp` call. (Both functions are local-scope; RETURN trap fires on any function exit.)

I4 — `validators/creator_engine_validator/pr_preflight.py` function
`_run_seat_ready_autogen_gate`: the autogen repair commit path when `autogen_artifact_changed=True`
needs broader end-to-end test coverage in `validators/tests/unit/test_pr_preflight.py`. The
existing test `test_seat_ready_autogen_gate_commits_only_regenerated_artifact` covers the CLI
autogen spec (`cli_reference_autogen_sync`) with `changed_paths` pointing at `pr_preflight.py`.
Add a companion test that covers the SCHEMA autogen spec path (`schema_reference_autogen_sync`)
end-to-end: use `changed_paths` that triggers `_schema_reference_surface_touched` (e.g. a path
under `schemas/`), set `autogen_artifact_changed=True`, and assert both the git-add and
pathspec-git-commit argv appear for the schema artifact. Extend `FakeRunner` as needed (e.g.
routing `gen_schema_reference.py --write` to the `autogen_generator_result` slot).

I5 — `validators/creator_engine_validator/pr_preflight.py` function `_commit_staged_autogen`:
verify (and if absent, add) that the git commit call includes the artifact pathspec so the
commit cannot sweep unrelated pre-staged index content under `--allow-dirty`. Expected argv
shape: `["git", "commit", "-m", "chore: refresh <check_name> artifact", "--", "<artifact>"]`.
If origin/main already carries this fix (check the runner call in the function body), confirm
it in the PR body and move on; do not add a duplicate fix. If absent, add `"--", str(spec.artifact)`
to the `runner(...)` call and ensure the existing test
`test_seat_ready_autogen_gate_commits_only_regenerated_artifact` asserts the pathspec is present.

I6 — `validators/creator_engine_validator/pr_preflight.py`, two NITs:

  I6a — The `SEAT_READY_TEST_COMMAND` constant is built via `.replace("-n auto", "-n 4", 1)`.
  There is currently no module-level assertion or dedicated test that pins this substitution.
  Add a unit test (or extend `test_seat_ready_default_test_command_caps_pytest_workers` in
  `validators/tests/unit/test_pr_preflight.py`) that directly asserts:
  `"-n auto" not in pr_preflight.SEAT_READY_TEST_COMMAND` and
  `f"-n {pr_preflight.SEAT_READY_PYTEST_WORKER_CAP}" in pr_preflight.SEAT_READY_TEST_COMMAND`.

  I6b — Functions `_cli_reference_surface_touched` and `_schema_reference_surface_touched`: the
  set literals `cli_paths` and `schema_paths` are built from `str(...)` on Path objects (e.g.
  `str(cli_autogen.GENERATOR_RELATIVE)`) without running those values through
  `_normalize_changed_path`. On POSIX hosts this is harmless, but for consistency the set
  members should be pre-normalized: `{_normalize_changed_path(str(cli_autogen.GENERATOR_RELATIVE)),
  _normalize_changed_path(str(cli_autogen.DOC_RELATIVE)), ...}`. Adjust the companion tests in
  `validators/tests/unit/test_pr_preflight.py` if any surface-path assertion strings change.

I7 — Test-isolation race under `pytest -n auto`:
  `test_surface_determinism_ignores_stale_checkout_artifact_dirs` lives in
  `validators/tests/unit/test_wheel_bake.py` and creates `validators/build/` inside the real
  repo checkout during its run (either directly or via `_assert_surface_deterministic` calling
  `_remove_checkout_build_artifacts` on the real root). Concurrently,
  `test_release_finalize_docs_copy_passes_release_guards` in
  `validators/tests/integration/test_release_finalize_integration.py` does
  `shutil.copytree(REPO_ROOT, ...)` and dies on the transient dir.

  Fix: isolate `test_surface_determinism_ignores_stale_checkout_artifact_dirs` so it never
  mutates the real repo root. The function already calls `_copy_repo_fixture(repo_root, tmp_path)`
  to obtain `fixture_root`; ensure that ALL subsequent calls (including those inside
  `_assert_surface_deterministic`) operate exclusively on `fixture_root`, not on the real
  `repo_root`. Inspect `_remove_checkout_build_artifacts` call sites inside
  `_assert_surface_deterministic` to confirm the parameter being passed is `fixture_root` not
  `repo_root`. If any call still references the real root, replace it with the fixture copy.
  After the fix, verify by running the two named tests together under `-n 8` five times with
  zero flakes and note the command + result in the PR body.

## Authorized path list

The unit MAY ONLY touch the following files. Any change outside this list is out of scope:

- `deploy/dgx-runsc/build-image.sh`
- `deploy/singleton-redeploy/smoke-singleton-redeploy.sh`
- `deploy/singleton-redeploy/redeploy-singleton.sh`
- `validators/creator_engine_validator/pr_preflight.py`
- `validators/tests/unit/test_pr_preflight.py`
- `validators/tests/unit/test_wheel_bake.py`
- `.ce/pr-manifests/ce-followups2-20260708.md`   ← carrier; slug MUST equal branch exactly
- `.ce/changelog/ce-followups2-20260708.md`       ← changelog fragment

`validators/tests/integration/test_release_finalize_integration.py` is referenced as context
for I7 (the victim of the race) but should NOT need modification if the fix is applied to
`test_wheel_bake.py`.

## Obligations

Changelog `.ce/changelog/ce-followups2-20260708.md`; carrier `.ce/pr-manifests/
ce-followups2-20260708.md` (slug == branch `ce-followups2-20260708`, every changed path listed,
exactly ONE `- **Declared work class:** story` line). PR body cites PR #895 (I2, I3) and PR #896
(I4, I5, I6) as source reviews. Note in the PR body per item: what was found, what was changed,
and verification evidence. For I7: include the 5× `-n 8` repro command and its output.

Preflight directive (ce-ops#303): run FULL `ce validate-pr` with CI-parity settings before
pushing: `TMPDIR=$HOME/tmp ce validate-pr --base origin/main --profile seat-ready` (or equivalent
with `--allow-dirty` if needed for the autogen repair gate). Gate must be GREEN locally.

## Stop line

Touch ONLY the eight authorized files listed above. Do not modify any host-ops-broker surface,
any deploy/systemd/ surface, any docs/, any release-staging, or any other path. Do not approve,
merge, or sign anything. Do not add scope items discovered in passing — open a ticket instead.
No gate acts. Signal: `READY ce-followups2-20260708 <sha> PR#<n>` on completion,
`BLOCKED ce-followups2-20260708 <reason>` if stuck.
