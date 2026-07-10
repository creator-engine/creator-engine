# BRIEF — REWORK PR #778 (ce-437-s3-containerize-daemons) — 4 blocking review findings
Role: implementer. Runs AS A CONCURRENT BATCH ITEM alongside your in-flight ce-a3-docs-envelope-tiers task — file-disjoint, use a SEPARATE worktree. Claim: ce-437-s3-rework-778.

## Setup
Your S3 work was harvested and is live as PR #778, branch `ce-437-s3-containerize-daemons`, LIVE HEAD `c36e1a46911c1cb27cd4b9e18f7b2387ad6bdc49` (your commit 70753e34 + one controller-side carrier commit c36e1a46 on top — base your rework on YOUR local 70753e34 in /var/tmp/wt-ce437s3; the controller cherry-picks only your NEW commits onto the live head at harvest, so do NOT recreate or rebase the existing commits).

## Review findings to fix (embedded — full review lives on the PR, which you cannot read)
1. BLOCKING — daemon_lease.py `_lease_is_live` (~:324-329): after `now - heartbeat_at > ttl_seconds` it returns False WITHOUT consulting `_pid_exists` for same-host leases. With TTL=300s, conveyor heartbeating once per run_once pass, and single validate-pr items running up to ~600s (your own module docstring), a LIVE same-host daemon becomes takeover-eligible mid-pass → two winners under allow_takeover=True. Fix: same-host liveness must check PID regardless of TTL elapse (remote-host leases may keep TTL-only semantics — document why). Add the regression test: expired-TTL + alive-PID same-host lease → NOT stale, takeover refused.
2. BLOCKING — conveyor_daemon.py run_once (~:355-365): heartbeat cadence is once per pass, not bounded by item processing time. Fix: heartbeat at minimum per item boundary (before each item), or adopt the supervisor-cadence pattern your own launch-queue-daemon.sh:197-226 already implements for the queue daemon. The lease contract this PR locks in must keep a live holder's heartbeat ahead of TTL under documented worst-case item duration.
3. BLOCKING — no test exercises the queue-daemon supervisor's fail-closed kill path (launch-queue-daemon.sh:213-224: heartbeat DaemonLeaseError → terminate child → exit 74). Add a test forcing that branch (simulated heartbeat loss; assert child termination semantics + exit code 74). A shell-level harness test or a python test of the supervisor loop extracted/invoked appropriately both acceptable — pick the one that tests the REAL code path, not a reimplementation.
4. BLOCKING — no test for lease-loss-mid-run in ConveyorDaemon.run_once(): add heartbeat() raising mid-pass → further item processing STOPS (fail closed), not silent continue. (Wire the heartbeat-per-item from fix 2 into this test.)

## Non-blocking (fix if cheap, else note in done-report)
5. `.lease.op.lock` meta-lock: crash mid-operation wedges acquire/heartbeat until manual delete (fails closed, OK) — document the recovery step in deploy/daemons/README.md or RELOCATION.md.
6. launch-queue-daemon.sh:91 default bin `v3_cli` → should default `cev3` (actual console-script; module-path fallback currently papers over it).

## Constraints
- Extend-don't-weaken: all existing lease race/takeover tests and the #410 armed-mode refusal seams stay intact; your fix must not loosen any predicate.
- File scope: daemon_lease.py, conveyor_daemon.py, test_daemon_lease.py, test_conveyor_daemon.py, launch-queue-daemon.sh, deploy/daemons/README.md or RELOCATION.md, changelog fragment. NOTHING else. Absolutely disjoint from your A3 task's forge/automerge files — keep the two worktrees separate.
- Changelog: append a rework note to .ce/changelog/ce-437-s3-containerize-daemons.md.

## Preflight + signal (standing, ce-ops#303)
FULL `ce validate-pr` GREEN in ONE pass before commit-for-harvest (iterate with .venv/bin/python -m pytest validators/tests/unit/test_daemon_lease.py test_conveyor_daemon.py first). Then commit and emit exactly:
`READY-FOR-HARVEST ce-437-s3-containerize-daemons <full-40-hex-sha> REWORK`
If blocked: `BLOCKED ce-437-s3-rework-778 <one-line reason>`.
