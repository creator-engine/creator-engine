# BRIEF — ce-445-c5prep-daemon-smoke — stateful daemon-container smoke + ownership-contract docs (QUEUED UNIT 4)

Role: implementer (dev-4, contained, foreman mode). UNIT 4 — start after your ce-434 unit signals,
AND only once a `git fetch origin` shows origin/main CONTAINS both f5ceefc0 (G9 uid model) and
4d7e12e2 (G10 image deps) — both are approved and merging now; poll fetch until true. Branch
`ce-445-c5prep-daemon-smoke` off that freshly-fetched origin/main.
Worktree /var/tmp; venv `.venv/bin/python -m pytest`, PYTHONPATH=validators, TMPDIR=/var/tmp.

## Why (embedded — you cannot read ce-ops)
Containerized merge-gate cutover attempt #1 halted on the two gaps you fixed (G9/G10). Before
retry, the cutover checklist gains one more gate: a STATEFUL smoke — attempt #1 only proved
plumbing on first contact; nothing exercises a daemon container stopping and restarting against
pre-existing host state. Three independent reviewer follow-ups from your G9/G10 PRs fold in here.

## Deliverables (one bounded unit)
1. Stateful smoke: a runnable script `deploy/daemons/smoke-daemon-container.sh` (or equivalent)
   that, given a scratch state root: (a) prepares state via the launcher path, (b) starts the
   daemon container in one-shot/dry mode, (c) stops it, (d) restarts against the SAME state root,
   and asserts: lease acquired→released→re-acquired cleanly, state files stay owned by the image
   uid, tmpfs secret path absent after stop. Must be skippable/refuse-with-message when docker is
   unavailable (it will NOT run in your container — that is expected; write it for the host
   operator and add unit tests that pin the script's option/invocation contract the same way
   test_daemon_lease.py pins the launcher).
2. `deploy/daemons/README.md`: add the uid/ownership contract section (CE_DAEMON_IMAGE_UID,
   default 10001; first boot under docker as non-root REFUSES with the `chown -R <uid>:<uid>
   <state_root>` remediation — copy the contract from your G9 run-daemon-container.sh changes so
   the README-only reader is not surprised at first boot).
3. Unit-test the G9 reviewer's uncovered branch if cheaply hermetic: missing-state-root creation
   under engine=docker for a non-root caller (skip-if-root guard). If not cheaply hermetic, note
   why in the PR body instead — do not force it.
4. Tiny parity nit from the G10 review: align the `command -v gh/git` vs `--help` check ORDER
   between deploy/oci/Dockerfile and deploy/runtime-image/Dockerfile (pick one order, keep tests
   passing).

## Allowed paths
deploy/daemons/ (script + README) · deploy/oci/Dockerfile · deploy/runtime-image/Dockerfile ·
validators/tests/unit/ (smoke-contract + daemon-lease + image tests) ·
.ce/changelog/ce-445-c5prep-daemon-smoke.md · .ce/pr-manifests/ce-445-c5prep-daemon-smoke.md

## STOP lines
- ⛔ Do NOT touch launch-queue-daemon.sh policy/authority logic, wall-secret handling, or any
  approval/merge seam — this unit is smoke + docs + test parity only.
- ⛔ Never sign anything with any key; a signed-artifact gate failure = STOP and report bytes.
- ⛔ No review/approve/merge/enqueue. You are not alone in the codebase; do not revert others' edits.

## Evidence bar
Full `ce validate-pr` (CI-parity) GREEN in ONE pass before commit-for-harvest — run it on your
side even though the carrier check is controller-side; if the ONLY failure is the path-manifest
carrier gate, that is the known contained-seat gap (your ce-434 fixes it) — say so explicitly.
Changelog fragment + carrier authored (controller re-verifies at harvest). Declared work class:
story. Signal: `READY-FOR-HARVEST ce-445-c5prep-daemon-smoke <40-hex sha>`.
