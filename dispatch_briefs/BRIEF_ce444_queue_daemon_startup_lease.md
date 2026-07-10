# BRIEF — ce-444-queue-daemon-startup-lease — fail-closed singleton lease for queue-daemon

Role: implementer (dev-4, contained). Branch: `ce-444-queue-daemon-startup-lease` off freshly-fetched
origin/main. Worktree under /var/tmp. venv: `.venv/bin/python -m pytest`, PYTHONPATH=validators, TMPDIR=/var/tmp.

## Why (embedded — you cannot read the ticket)
Operator ratified today: live merge-gate authority (queue-daemon + approval-wall) is a policy
SINGLETON. Evidence: queue-daemon has NO mutual-exclusion seam (convention only); capability-marker
minting is an unguarded read-modify-write of the PR body (integrator_belt._upsert_approval_capability_marker
→ _update_pr_body) so two live instances race with lost-update semantics; approval-settle windows
are per-instance local state → duplicate enqueues. The conveyor daemon already has the right
pattern: DaemonLease (validators/creator_engine_validator/forge/daemon_lease.py — O_EXCL atomic
acquire, allow_takeover=False, heartbeat, DaemonLeaseHeld/DaemonLeaseStale). Turn the convention
into code for queue-daemon.

## Deliverable
1. `_cmd_queue_daemon` (v3_cli.py, ~:4795): acquire a DaemonLease at startup BEFORE the first
   pass; heartbeat it each pass; release in finally. allow_takeover=False (fail-closed).
2. New flag `--daemon-lease-root <dir>` (default: derive from the approval-wall state path's
   parent, e.g. <state-dir>/queue-daemon-lease/ — inspect how --approval-wall-state is resolved
   and co-locate; the container form already exports CE_DAEMON_LEASE_ROOT — honor that env as the
   default source if set, flag wins).
3. Lease default-ON (the singleton policy is the point). Held lease → ONE clean stderr line naming
   lease path + holder pid, exit 73. Stale lease → same shape, exit 73, message says verify-dead-
   then-remove (mirror the conveyor RUNBOOK.md recovery wording; do NOT auto-takeover).
4. Tests (extend test_v3_cli.py or the queue-daemon test module — find where _cmd_queue_daemon is
   tested): behavioral — second acquire refuses with exit 73; heartbeat called per pass; release on
   clean exit; stale-lease refusal. Use the existing DaemonLease test fakes/patterns from
   test_conveyor_daemon_runner.py as reference.
5. One short recovery note appended to deploy/queue-daemon/RELOCATION.md OR a new
   deploy/queue-daemon/RUNBOOK.md (match the conveyor runbook shape; product lens, no ticket refs).

## Constraints
- Files (closed set): validators/creator_engine_validator/v3_cli.py · the queue-daemon test module
  you identify (name it in the carrier) · daemon_lease.py ONLY if a small shared helper is genuinely
  needed (prefer not; it is in-flight-adjacent) · deploy/queue-daemon/RUNBOOK.md or RELOCATION.md ·
  changelog + carrier. Do NOT touch conveyor_daemon_runner.py / launch-conveyor-daemon.sh /
  deploy/conveyor-daemon/ (claimed by dev-3 tonight) or conveyor_daemon.py.
- The disarmed/--dry-run daemon path must ALSO take the lease (decision: shadow instances contend
  too — two dry-runs are harmless but the lease keeps the model simple; if this breaks an existing
  dry-run test expectation, note it in the changelog and keep lease-on-dry-run).
- ⛔ Signed-artifact stop-line: signature-gate failure → STOP + report bytes; never sign.
- Work class: story. Bounded ≤ ~300 LOC.

## Preflight
FULL `ce validate-pr` GREEN one pass before commit-for-harvest.

## Evidence + signal (no push auth — controller harvests)
Commit `gate: fail-closed startup lease for the merge-queue daemon`, emit:
`READY-FOR-HARVEST ce-444-queue-daemon-startup-lease <40-hex sha>`.

## Stop line
No push/PR/review/signing. Controller harvests on signal.
