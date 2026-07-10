# DISPATCH — dev-3 — 2026-07-10 — unit: hashpin CI visibility — class S
Role: implementer foreman. Signal: `READY-FOR-HARVEST ce-453b-hashpin-ci-visibility <full-40-hex-sha>`
or `BLOCKED ce-453b-hashpin-ci-visibility <one-line-reason>`.

**START-GATE:** do NOT start until origin/main contains commit 3739b552da (check:
git fetch origin main; git merge-base --is-ancestor 3739b552da16c20095c06cb05528417966768f8d origin/main
— exit 0 = GATE-OPEN). Poll every ~5 min; read and plan while waiting. The gated commit merges
soon; it touches the same files this unit edits.

Branch `ce-453b-hashpin-ci-visibility` off freshly fetched origin/main AT-OR-AFTER the gate-open
commit. Worktree /var/tmp/wt-ce-453b-hashpin-ci-visibility. Standing preflight directive: run
`ce validate-pr --profile contained-seat` if your environment can; else focused tests +
BLOCKED(env) per protocol. PRE-SIGNAL CHECKLIST: focused tests green + confidentiality check:
`python -m pytest validators/tests/unit/test_public_docs_confidentiality.py::test_tracked_text_files_contain_no_new_confidential_or_internal_references -q`

## Context (embedded)

In validators/creator_engine_validator/checks/signed_artifact_pins.py the REGISTERED check
entrypoint `run(paths)` (around line 268) is a NO-OP stub returning an empty CheckResult, while
the real verification lives in `run_with_base` and the gate subcommand. Consequence: CI's
registered-checks pass (the "Validate" workflow) is structurally blind to signed-artifact pin
corruption — a defect in this class red-lit every LOCAL validate while CI stayed green on main
all day (live incident 2026-07-10). This unit closes the CI blindspot plus two review-noted test
gaps from the fix PR that just merged ahead of you.

## Unit

1. Implement `run(paths)` to execute the real repo-scan verification (reuse
   discover_pins / run_with_base internals in repo-scan mode; fail closed on corruption exactly
   like the gate path; keep runtime bounded — it parses one file plus pinned-path hashing).
2. Harden the real-file regression test in validators/tests/unit/test_signed_artifact_pins.py to
   assert ALL THREE pins by name including `content_sha256` (currently asserts only >= 2 and two
   names).
3. Fix test_run_explicit_file_path_still_checks_malformed_examples in
   validators/tests/unit/test_path_manifest_fidelity.py — it claims to prove explicit-path
   checking of examples/malformed/** but places its fixture at tmp_path root; relocate the
   fixture under <tmp>/examples/malformed/ so the docstring is honest.

## Files (allowed writes)

- validators/creator_engine_validator/checks/signed_artifact_pins.py
- validators/tests/unit/test_signed_artifact_pins.py
- validators/tests/unit/test_path_manifest_fidelity.py
- .ce/changelog/ce-453b-hashpin-ci-visibility.md — changelog fragment
- .ce/pr-manifests/ce-453b-hashpin-ci-visibility.md — carrier (slug=branch) with exactly
  `- **Declared work class:** S`

## Stop lines

Do not weaken any fail-closed path. Do not touch docs/llms-install.md (SIGNED artifact). No
push, no sign. pr_preflight.py and all other checks/ modules untouched. `.github/**`,
`deploy/**`, `forge/**`, brain ledger untouched.

## Signal

After focused tests pass and the confidentiality check is green:
1. Commit all changes on branch `ce-453b-hashpin-ci-visibility`. Commit early and often.
2. Signal: `READY-FOR-HARVEST ce-453b-hashpin-ci-visibility <full-40-hex-sha>`

**In-seat validation note:** use absolute /workspace/creator-engine/.venv/bin/ce and
/workspace/creator-engine/.venv/bin/python — bare `ce` does not resolve after relaunch.

## AMENDMENT — continuity standby — 2026-07-10T16:46Z

STOP polling the original SHA ancestry gate.  PR #956 is merged and its intended
content is on main, but GitHub's merge transformation means head SHA
`3739b552da16c20095c06cb05528417966768f8d` is not an ancestor object in main;
the original gate can never open as written.

Do not start implementation yet.  A live territory audit found the already
delivered and queued branch `ce-f1s2-preflight-env-propagation` also edits
`validators/creator_engine_validator/checks/signed_artifact_pins.py`.  This unit
is now serialized behind f1s2 landing.  Stop the polling loop and report:

`BLOCKED-ON-PRECURSOR ce-453b-hashpin-ci-visibility ce-f1s2-preflight-env-propagation`

The controller will issue a fresh hash-pinned resume amendment after f1s2 lands
and re-verify novelty against then-current main.  Make no source edit, commit,
push, carrier, or worktree change under this amendment.
