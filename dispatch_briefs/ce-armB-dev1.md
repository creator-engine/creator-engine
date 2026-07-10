# BRIEF — dev-1 — ARM-B: broker --run-mode CLI + service (ce-ops#346 / APPROVE arming)

Born-foreman, non-contained (SELF-PUSH as ce-dev-1). Drive to a green PR.

## Goal
Implement ce-ops#346: wire a `--run-mode` CLI flag into the egress self-review broker so the daemon CAN be told "strangeLoop" (which is what enables autonomous APPROVE, per the merged #349/#350 authority chain). It MUST default to "dev" (fail-safe) so APPROVE stays refused until the Operator explicitly arms it. You are making APPROVE ARMABLE; you ARM nothing.

## Context (verified on origin/main)
- The broker's Python API already threads run_mode (parse_request/submit_self_review/serve/SelfReviewServer all accept it), and cred_injection_proxy.py already gates APPROVE on `_APPROVE_PERMITTING_RUN_MODES = {"strangeLoop"}` + envelope validation (#349/#350, merged).
- THE GAP: `_build_parser()` in tools/egress-broker/ce_egress_self_review_broker.py has NO `--run-mode` argument, and `main()` calls `serve(...)` WITHOUT passing run_mode → daemon always starts run_mode=None → `_is_strangeloop(None)` is False → APPROVE always refused. There is no way to activate strangeLoop on the running daemon.

## SAFETY INVARIANT
- `--run-mode` MUST default to "dev" (or None→treated as dev). Only an explicit `--run-mode strangeLoop` enables the APPROVE path. The author≠approver host-side wall + reviewer-authority-envelope validation REMAIN and are unaffected. Validate the flag value against the RunMode enum (grading_policy.py: only "dev"/"strangeLoop" valid); reject unknown values fail-closed.

## Branch
`ce-346-broker-run-mode-cli` off CURRENT origin/main (git fetch origin main first). Fresh worktree.

## Scope
1. `tools/egress-broker/ce_egress_self_review_broker.py`: add `--run-mode` to `_build_parser()` (choices = dev/strangeLoop, default dev); in `main()`, read it and pass `run_mode=args.run_mode` through to `serve(...)` / `SelfReviewServer`. Validate against the RunMode enum, fail-closed on invalid.
2. `deploy/systemd/ce-egress-self-review.service`: add `--run-mode ${CE_EGRESS_RUN_MODE}` to the ExecStart (parameterized via an Environment= default of `CE_EGRESS_RUN_MODE=dev`), so arming is a deliberate env change + restart, NOT a code change. Keep the default dev.
3. Tests in validators/tests/unit/ (the broker test file): assert (a) default/absent --run-mode → run_mode dev → APPROVE refused; (b) `--run-mode strangeLoop` → run_mode reaches serve/SelfReviewServer (the daemon is told strangeLoop); (c) invalid --run-mode value → fail-closed reject. Do NOT weaken any existing author≠approver / envelope test.

## Allowed paths (HARD limit)
- `tools/egress-broker/ce_egress_self_review_broker.py`
- `deploy/systemd/ce-egress-self-review.service`
- the broker's unit test file under `validators/tests/unit/`
- `.ce/changelog/ce-346-broker-run-mode-cli.md`, `.ce/pr-manifests/ce-346-broker-run-mode-cli.md`
Do NOT touch cred_injection_proxy.py, ce_cli.py, or the actuator.

## Evidence
- FULL preflight GREEN: `rm -rf validators/*.egg-info validators/build; TMPDIR=/var/tmp PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr --head-ref ce-346-broker-run-mode-cli`
- Carriers via carrier_gen (dashed slug); single carrier; manifest+body `- **Declared work class:** story`.
- SELF-PUSH as ce-dev-1, open PR (mention ce-ops#346; note this is the APPROVE-arming ENABLER and stays dev-default), report PR# + SHA. ARM nothing; default stays dev. No approve/merge. Stay in allowed paths.
