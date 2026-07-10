# BRIEF — ce-445-daemon-container-test-gaps — close the daemon-container plumbing review's test gaps

Role: implementer (dev-4, contained). Branch: `ce-445-daemon-container-test-gaps` off
freshly-fetched origin/main. Worktree under /var/tmp (NOT /workspace). venv has no activate →
`.venv/bin/python -m pytest`, PYTHONPATH=validators, TMPDIR=/var/tmp.

## Context (embedded — you cannot read PRs/tickets)
`deploy/daemons/run-daemon-container.sh` (merged to main 2026-07-04) gained:
- `CE_DAEMON_ENV_FILE`: host env file staged into the container; contract requires it to EXIST and
  be 0600 — the launcher must refuse cleanly when it is missing.
- `CE_DAEMON_CACERT_FILE`: host CA cert ro-mounted with BAO_CACERT repointed — same
  must-exist refusal contract.
Its existing tests live in `validators/tests/unit/test_daemon_lease.py`, including a
byte-identical "no new vars → invocation unchanged" compat test for the queue-daemon path —
follow those exact patterns. Independent review flagged three NON-BLOCKING coverage gaps.

## Deliverables (exactly these three tests, in validators/tests/unit/test_daemon_lease.py)
1. Refusal when CE_DAEMON_ENV_FILE names a missing file: clean single-line error naming the path,
   nonzero exit, and NO container invocation attempted.
2. Same shape for CE_DAEMON_CACERT_FILE naming a missing file.
3. Byte-identical default-invocation pin for the CONVEYOR-daemon path: with none of the new vars
   set, the rendered invocation for conveyor-daemon is byte-identical to the pre-plumbing form
   (mirror the existing queue-daemon compat pin).

## Constraints
- Files (closed set): validators/tests/unit/test_daemon_lease.py ·
  .ce/changelog/ce-445-daemon-container-test-gaps.md ·
  .ce/pr-manifests/ce-445-daemon-container-test-gaps.md.
- Do NOT touch run-daemon-container.sh itself, v3_cli.py, test_integrator_belt.py, or any
  conveyor file. If a test cannot pass without changing run-daemon-container.sh, that is a
  product finding → signal `BLOCKED ce-445-daemon-container-test-gaps <reason>`, don't widen.
- ⛔ Signed-artifact stop-line: any signed-artifact gate failure → STOP and report; never sign.

## Preflight + known container env gaps (standing)
Run the FULL `ce validate-pr`. Your container is KNOWN to lack ssh-keygen (install-spec signature
guard) and libsodium (PCO-024 / examples gates) — those failures are FALSE-RED environment gaps,
tracked upstream. Protocol: if the ONLY validate-pr failures are those known env-gap gates AND
`test_daemon_lease.py` passes fully, commit and signal with a preflight note (see below). Any
OTHER failure → fix it or signal BLOCKED.

## Evidence + signal (no push auth — controller harvests)
Commit `ce-ops#445 follow-up: env-file/cacert refusal tests + conveyor invocation pin`, then emit:
`READY-FOR-HARVEST ce-445-daemon-container-test-gaps <40-hex sha>` — append
` PREFLIGHT-NOTE envgap:<gate names>` if the known env gaps fired.
Work class: tiny (expected) or story. Changelog + carrier (carrier_gen API, stem == branch).

## Stop line
No push, no PR, no review, no signing. Controller harvests on signal.
