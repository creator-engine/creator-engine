# BRIEF — ce-388-fastfollow-lease-ux — A1 daemon fast-follows (ce-ops#443, embedded below)

Role: implementer (dev-3, contained). Branch: `ce-388-fastfollow-lease-ux` off freshly-fetched
origin/main. Worktree under /var/tmp (NOT /workspace). venv has no activate → `.venv/bin/python -m pytest`.

## PRECONDITION (your origin/main is stale)
`git fetch origin main` FIRST, branch from origin/main, and verify
`validators/creator_engine_validator/conveyor_daemon_runner.py` exists at your branch tip (it merged
to main 2026-07-04 17:10Z). If absent after fetch, signal `BLOCKED ce-388-fastfollow-lease-ux fetch-failed`.

## Deliverables (independent-review findings on the A1 daemon — full context embedded, no ticket access needed)
1. **DaemonLeaseError handler in main()** — conveyor_daemon_runner.py (~:383-388): direct
   `python -m creator_engine_validator.conveyor_daemon_runner` with a held/stale lease currently
   surfaces a raw traceback, exit 1. The shell launcher (deploy/conveyor-daemon/launch-conveyor-daemon.sh
   ~:140-148) already catches DaemonLeaseError → clean message + exit 73. Make main() match: catch
   the DaemonLeaseError family, print one clean stderr line naming the lease path + holder pid,
   exit 73 (consistent with the launcher). Do not change acquire() semantics (allow_takeover stays False).
2. **Test for it** — test_conveyor_daemon_runner.py: behavioral test where acquire() raises
   DaemonLeaseHeld → assert the clean message and exit code 73; same for DaemonLeaseStale.
3. **Rename the misleading `--dry-run` flag** in launch-conveyor-daemon.sh (~:221): it sets
   CE_CONVEYOR_DAEMON_ITERATIONS=1 but the daemon still runs armed (pushes branches, opens PRs).
   Rename to `--one-shot`; make `--dry-run` an ERROR with a message pointing to --one-shot and
   explaining the daemon has no disarmed launcher mode (fail-closed beats silent misnomer; the
   script merged <1h ago, no compat burden). Update the usage() text.
4. **Stuck-lease recovery runbook** — NEW file deploy/conveyor-daemon/RUNBOOK.md: the heartbeat
   thread exits via os._exit(74) on failure, bypassing lease.release(); after any crash the lease
   file persists, restarts fail with DaemonLeaseStale (fail-closed, deliberate), and recovery =
   verify the old pid is dead → remove the lease file → restart. Document: symptom (exit 73 loop,
   journal signature), verification steps, recovery command, and WHY takeover is not automatic.
   Product lens: no internal ticket references in the file.

## Constraints
- Files (closed set): validators/creator_engine_validator/conveyor_daemon_runner.py ·
  validators/tests/unit/test_conveyor_daemon_runner.py · deploy/conveyor-daemon/launch-conveyor-daemon.sh ·
  deploy/conveyor-daemon/RUNBOOK.md · .ce/changelog/ce-388-fastfollow-lease-ux.md ·
  .ce/pr-manifests/ce-388-fastfollow-lease-ux.md. Anything else needed → BLOCKED signal, don't widen.
- Do NOT touch conveyor_daemon.py or test_conveyor_daemon.py (claimed by dev-4 slice-10 work),
  the service unit, run-daemon-container.sh, docs/, or any signed artifact.
- ⛔ Signed-artifact stop-line: if any gate fails on a signed artifact (SSHSIG/SHA256SUMS/
  content_sha256), STOP and report the bytes — never sign; ce-root-v1 is controller-only.
- Shadow invariants stay intact: no approve/merge/enqueue seams; the forbidden-strings guard test
  must still pass untouched.
- Changelog required; carrier via carrier_gen API write_carriers(base=<merge-base vs origin/main>),
  stem == branch name. Work class: pick minimal compliant vs the sizing floor (enum
  tiny|story|feature|epic; expect tiny or story).

## Preflight (standing ce-ops#303)
FULL `ce validate-pr` GREEN in ONE pass before commit-for-harvest.

## Evidence + signal (no push auth — controller harvests)
Commit `ce-ops#388 fast-follow: lease-error UX, one-shot flag, recovery runbook`, then emit:
`READY-FOR-HARVEST ce-388-fastfollow-lease-ux <40-hex sha>`.

## Stop line
No push, no PR, no review, no signing. Controller harvests on signal.
