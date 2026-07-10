# BRIEF — dev-4 — Surface A arming wiring: CI materialization + change_ref (ce-ops#313 arming-completion)

Born-foreman, contained/no-egress (DO NOT push — controller harvests). Fresh branch `ce-armA-arming-wiring` off CURRENT origin/main (git fetch origin main first). Drive to READY-FOR-HARVEST GREEN.

## Mission
Make the auto-merge arming path actually REACH the CI actuator — while staying 100% INERT until the Operator sets a GitHub Actions Variable. Today both `automerge-decide.yml` and `automerge-actuate.yml` read `.ce/state/automerge/policy.json`, which is gitignored + absent in CI → both default to `run_mode="dev"` → Dormant. So "arming" reaches nothing. You will add the missing input wire + fix the decision-artifact change-ref fields.

## SAFETY INVARIANT (non-negotiable — this is an arming control)
- Your wiring MUST default to DORMANT/dev. When the Variable is unset or `"dev"`, the materialized policy is `run_mode=dev` (or no file) → actuator stays Dormant. Only an explicit `"ceo"` Variable arms.
- You MUST NOT set/flip the Variable, set run_mode=ceo anywhere committed, or arm anything. Arming = the Operator setting the Variable later. You make it ARMABLE; you arm nothing.
- Fail-safe: if the materialization step errors or the Variable is malformed, the policy must end up dev/dormant, never armed.

## Part 1 — Materialization (both workflows)
In BOTH `.github/workflows/automerge-decide.yml` and `.github/workflows/automerge-actuate.yml`, add a step BEFORE the Python validator invocation that writes `.ce/state/automerge/policy.json` from Operator-controllable GitHub Actions repo Variables:
- `vars.CE_AUTOMERGE_RUN_MODE` → policy `run_mode` (default `"dev"` if unset).
- `vars.CE_AUTOMERGE_ENABLING_REF` → policy `enabling_decision_ref` (the ratification record; required non-empty for arming; leave null if unset).
- Set `kill_switch: false`, and the docs-class flag `classes.docs.auto_merge: true` ONLY when run_mode is ceo (so docs-class is the armed scope). When run_mode=dev, write a fully-dormant default policy.
- Write the JSON to the path the loader reads (`.ce/state/automerge/policy.json` relative to repo root / runner CWD). Mirror the exact schema `AutoMergePolicyState`/`from_payload` expects — study `forge/automerge_policy.py`.
The decide step and the actuate step must BOTH see the materialized policy (decide stamps run_mode into the artifact; actuate re-verifies live policy). Keep the materialization identical/shared between the two workflows.

## Part 2 — change_ref fields (verify, then fix if real)
FIRST verify the gap: does the actuator's `_change_ref` (in `forge/automerge_actuator.py`) refuse (`change_repo_invalid` / similar) when the decision payload lacks `repo`/`branch`/`base`? And does `AutoMergeDecision.to_payload()` (in `forge/automerge_policy.py`) omit them? If CONFIRMED:
- Stamp `repo`/`branch`/`base` into the decision artifact: source them in the decide WORKFLOW from GitHub context (`GITHUB_REPOSITORY`, `github.event.pull_request.head.ref`, `github.event.pull_request.base.ref`) → pass to the `ce automerge-decide` CLI (new args) → carry through `decide_automerge` into `AutoMergeDecision` → serialize in `to_payload()`.
- If NOT real (the fields are already present or not required), note that in your report and skip — do not invent changes.

## Tests
- Materialization: a test (or workflow-lint) proving Variable-unset → dev/dormant policy; `CE_AUTOMERGE_RUN_MODE=ceo` → armed policy with kill_switch=false + docs class flag + enabling_ref. Assert the dev default keeps the actuator Dormant.
- End-to-end (unit-level): with a materialized ceo policy + a docs-class, approved, green decision carrying repo/branch/base → actuator would actuate (or reaches `_enable_auto_merge`); without the Variable → Dormant. Use the existing actuator test patterns.
- change_ref: a test asserting the decision payload now carries repo/branch/base and the actuator accepts them.

## Scope / allowed paths
`.github/workflows/automerge-decide.yml`, `.github/workflows/automerge-actuate.yml`, `validators/creator_engine_validator/forge/automerge_policy.py`, `validators/creator_engine_validator/ce_cli.py` (automerge-decide handler only), the relevant `validators/tests/unit/test_automerge_*.py`, + the two carriers (`.ce/changelog/ce-armA-arming-wiring.md`, `.ce/pr-manifests/ce-armA-arming-wiring.md`). Do NOT touch the actuator's gate logic (automerge_actuator.py) beyond reading it, do NOT touch policy.json under .ce/state (gitignored), do NOT change required_checks.

## On READY
`rm -rf validators/*.egg-info validators/build` then `TMPDIR=/var/tmp PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr --head-ref ce-armA-arming-wiring` GREEN. Report: the materialization step (both workflows), whether change_ref was real + how fixed, the Variable names, the new tests, and `commit && echo SHA`. Do NOT push. Confirm everything stays dev/dormant by default.
