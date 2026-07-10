# DISPATCH BRIEF — ce-ops#383 — conveyor daemon argv hardening (residual)

- **Seat:** dev-3 (contained, ce-vps-codex)
- **Role:** implementer
- **Branch:** `ce-383-conveyor-argv-hardening` (off fresh `origin/main` — fetch first; you HAVE git egress)
- **Work class:** XS (declare `- **Declared work class:** tiny` in the PR body / changelog per gate format)
- **Worktree:** create under `/var/tmp/wt-ce383/` (NOT /workspace)

## Ticket (embedded — you cannot read ce-ops)

> **ce-ops#383: conveyor daemon: harden git/gh argv against option-smuggling (`--` terminator + validate remote/branch shapes)**
>
> Follow-up from PR #718 conveyor go-live adversarial re-review. The RCE via payload-supplied
> `validate_command` was fixed in #718 (pinned at daemon construction). Residual non-blocking
> hardening gap: payload-derived fields flow into git/gh argv without a `--` option terminator:
> - `item.remote`/`item.base`/`item.branch` → `git_runner(["push", item.remote, f"{landed.branch}:..."])`
> - title/body → `gh pr create ...`
>
> Argv (no shell) so classic shell injection impossible, but git option-smuggling theoretically
> possible (value beginning with `--` interpreted as a flag). Asks:
> 1. Insert `--` before positional args in the daemon's git/gh invocations (push, pr create where applicable).
> 2. Validate `remote`/`branch`/`base` shapes (reject leading `-`, enforce sane ref charset) before argv.
> 3. Regression tests: `--`-prefixed remote/branch payload must be rejected or neutralized.

## CONTROLLER SCOPE FINDING — do not rebuild what's landed

Main already carries (via #718 + #740 payload-as-data-only schema), in
`validators/creator_engine_validator/conveyor_daemon.py`:
- `_reject_git_argv_gadget(value, label=...)` — rejects values starting with `-` and values
  containing `::` (transport-helper shape), applied fail-closed to bundle_path, pr_base,
  base/remote/validate_command and branch shapes in the pre-action audit (`~line 535` audit block).

Therefore ask #2 is LARGELY DONE. Your residual scope:
1. **`--` terminators (defense-in-depth):** add `--` before positionals where the git command
   accepts it (e.g. `git push -- <remote> <refspec>`; check each invocation — rebase/checkout/etc.
   in conveyor.py land path too if payload-derived values reach them). For `gh pr create`, note
   title/body are option VALUES (after `--title`/`--body`) — verify with a test whether a
   `--`-leading title is safely consumed as a value by gh; if not neutralizable via argv order,
   document why shape-rejection is the effective control (title/body are free text — do NOT
   charset-restrict them; state the reasoning in the PR body).
2. **Ref charset validation:** tighten remote/branch/base beyond leading-`-`/`::` to a sane git
   ref charset (reuse/extend `_reject_git_argv_gadget` or add a sibling validator; follow
   `git check-ref-format` rules pragmatically — no spaces, no `..`, no control chars, no `~^:?*[\`,
   no leading/trailing `/` or `.lock` suffix). Keep it fail-closed with clear labels.
3. **Regression tests** in `validators/tests/unit/test_conveyor_daemon.py`: `--`-prefixed
   remote/branch/base rejected; ref-charset violations rejected; happy path unchanged.

## Allowed paths (exhaustive)
- `validators/creator_engine_validator/conveyor_daemon.py`
- `validators/creator_engine_validator/conveyor.py` (ONLY if payload-derived argv sites live there too)
- `validators/tests/unit/test_conveyor_daemon.py` (+ `test_conveyor.py` only if you touch conveyor.py)
- `.ce/changelog/ce-383-conveyor-argv-hardening.md` (REQUIRED)
- `.ce/pr-manifests/ce-383-conveyor-argv-hardening.md` — regen via
  `carrier_gen.write_carriers(base=<merge-base>)` API after `rm -rf validators/build validators/*.egg-info`; never hand-edit.

## Standing preflight directive (ce-ops#303)
Run the FULL local validator preflight (`ce validate-pr`, CI-parity) GREEN in ONE pass before
commit-for-harvest; do not discover gates via CI. venv has no activate — use `.venv/bin/python -m pytest`.

## STOP LINES
- NO daemon arming/config changes, NO flag flips, NO workflow edits.
- NO push from inside the container attempt beyond the broker path you normally use; if broker
  unavailable, commit locally and signal READY-FOR-HARVEST.
- Do NOT touch forge/automerge_* (dev-4 territory) or release/bump files (dev-1 territory).

## Expected evidence (done-report at /var/tmp/ce383-done-report.md)
- Commit SHA (`git commit && git rev-parse HEAD` — a done-report without a verifiable SHA is NOT done)
- `ce validate-pr` GREEN output tail
- Test names added + pass evidence
- The gh-title/body neutralization verdict (ask #1) with reasoning
- Signal `READY-FOR-HARVEST ce-383-conveyor-argv-hardening <SHA>` when complete.
