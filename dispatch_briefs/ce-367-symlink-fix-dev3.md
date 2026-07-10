# SEED BRIEF — dev-3 — PR #726 symlink-containment fix (ce-ops#367)

You authored the CE-native `ce init` (ce-ops#367), now open as PR #726 on branch
`ce-367-ce-native-init`. A governed adversarial review found ONE blocking
security defect. Fix exactly that, add a regression test, keep everything else
unchanged.

## The defect — symlink-following write-escape (CWE-59)
File: `validators/creator_engine_validator/project_init.py` (init_project /
plan_actions, ~lines 333-379).

Only the top-level `target` is `.resolve()`d (line ~364). Each per-template
`path = root / template.path` is then passed to `Path.exists()`,
`Path.is_file()`, `Path.mkdir(parents=True, exist_ok=True)`, and
`Path.write_text()` — all of which follow symlinks on intermediate path
components. So a symlink planted INSIDE the target (e.g. `<target>/.ce ->
/outside/writable`) makes `ce init` create/overwrite files OUTSIDE the target
root:
- Default mode, NO --force: every `.ce/**` template resolves through the `.ce`
  symlink, classifies as `"created"` (the safe path), then `mkdir`+`write_text`
  follow the link and write a `.ce/`-shaped tree outside the target.
- --force variant: a symlinked leaf file (`README.md -> ~/.bashrc`) is followed
  by `is_file()`, classified `"overwritten"`, and clobbered.

`ce init` is designed to run against existing/cloned dirs (your own
integration test `existing_project` fixture), so this escapes a governed
worker's worktree boundary — the worker-isolation defect class that must not
ship.

## The fix
Before acting on any per-template path, canonicalize it and confine it under the
resolved root:
- Compute `resolved = (root / template.path).resolve()` (root already resolved).
- Refuse with `ProjectInitRefused` if `not resolved.is_relative_to(root)` — i.e.
  if any intermediate component is a symlink pointing outside root, or the path
  otherwise escapes.
- Apply the check in BOTH `plan_actions` (so the `--json`/dry preview reflects
  the refusal) AND the `init_project` write loop (defense against the
  plan→write TOCTOU: plan_actions builds the list in one pass, init_project
  iterates in a second pass — re-validate at write time too).
- Prefer refusing the whole init on an escaping path over silently skipping, so
  the user sees a clear error (choose the message wording; make it actionable).

Keep the existing idempotency / user-edit-preservation / --force semantics for
in-root paths exactly as they are. Do NOT change the CLI surface, templates,
docs, or the gate-test edits — reviewers verified those are clean.

## Regression test (REQUIRED — test-coupling gate)
Add to `validators/tests/unit/test_project_init.py` (and/or the CLI test):
1. Plant `<tmp>/.ce -> <tmp_outside>` (dir symlink) before `init_project`,
   assert it refuses (ProjectInitRefused) and writes NOTHING under
   `<tmp_outside>`.
2. Plant `<tmp>/README.md -> <some_outside_file>` (file symlink), run with
   `force=True`, assert refusal and the outside file is untouched (byte-equal
   to before).
Optional (non-blocking nit from review): a PermissionError/OSError-on-write test
mapping to a clean `ProjectInitError` — add if cheap.

## Push mechanics (contained seat)
- Work in your worktree off the CURRENT branch tip. IMPORTANT: origin/main has
  advanced — the PR head was rebased at harvest to `a43429735`. Base your fix on
  the PUSHED branch head `ce-367-ce-native-init` (fetch it:
  `git fetch origin ce-367-ce-native-init` then branch off
  `origin/ce-367-ce-native-init`), NOT your old local commit `edf8a21c`, so the
  fix stacks on the harvested/rebased head.
- FULL `ce validate-pr` GREEN in ONE pass before signalling. Worktree source,
  PYTHONPATH=validators; `rm -rf validators/build validators/*.egg-info` first.
- Your self-push spine is now live (container relaunched). Push branch
  `ce-367-ce-native-init` via the broker (it's a `ce-` namespace branch, allowed).
  If self-push is refused for any reason, commit + signal READY-FOR-HARVEST with
  the SHA and the controller harvests.
- Update `.ce/changelog/ce-367-ce-native-init.md` with a line for the
  symlink-containment fix. Carrier path set is unchanged (same files) unless you
  add a new test file — if so, regen via carrier_gen `write_carriers(base=<merge-base>)`.

## REPORT
Pushed head SHA (or READY-FOR-HARVEST + SHA), preflight result (one-pass green?),
the two regression tests added + that they fail-without-fix / pass-with-fix,
any anomaly. STOP after push/signal — do NOT approve/merge.
