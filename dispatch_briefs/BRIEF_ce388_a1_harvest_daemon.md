# BRIEF — ce-ops#388 A1: shadow harvest-daemon leg (launcher + entrypoint wiring)

Role: implementer. Claim: ce-388-conveyor-harvest-daemon. Branch: `ce-388-conveyor-harvest-daemon`
off CURRENT origin/main. GATE: before starting, fetch origin/main and verify the 8c merge is in
your base: `git grep -q 'refusing to land unverified tree' origin/main -- validators/creator_engine_validator/conveyor_daemon.py`
— if absent, signal `BLOCKED ce-388-conveyor-harvest-daemon base-missing-8c` and stop.
Worktree: /var/tmp/ce-388-a1 (NOT /workspace). Venv has no activate — `.venv/bin/python -m pytest`.

## MANDATORY STOP LINE (read first)
Shadow mode ONLY. The daemon opens PRs but MUST NOT auto-approve, auto-merge, enqueue, or call
any approval-wall or reviewer-authority surface. Deployment (enabling the service, starting the
container) is a separate controller-gated step — deliver scripts + service file DISABLED
(no [Install] section). Do NOT modify: conveyor_daemon.py, daemon_lease.py, conveyor_discovery.py,
conveyor.py, or ANY existing test file.

## What you are building (self-contained — you cannot read ce-ops)
The conveyor autonomy lane builds a daemon that watches fleet seats for READY-FOR-HARVEST
signals and auto-opens PRs. Discovery merged (#775, conveyor_discovery.py). Armed validation
via sandbox + fail-closed tree guards merged (8c). You build the LAUNCHER and ENTRYPOINT that
assemble the existing ConveyorDaemon(armed=True) from its required seams and run it as a
containerized daemon. NO new core logic — wiring + deployment scaffolding only.

## Substrate (read from your origin/main checkout FIRST)
- validators/creator_engine_validator/conveyor_daemon.py (ConveyorDaemon ctor, run_once, armed seams)
- validators/creator_engine_validator/conveyor_discovery.py (ConveyorSeatDiscoveryRunner, SeatProbeSpec)
- validators/creator_engine_validator/daemon_lease.py (acquire, DaemonLease, DEFAULT_LEASE_TTL_SECONDS)
- validators/creator_engine_validator/forge/daemon_allocation.py (DaemonPathAllocator, DaemonRuntimeRoots)
- validators/creator_engine_validator/validation_sandbox_receipt.py (ValidationSandboxReceiptIssuer)
- deploy/daemons/run-daemon-container.sh (canonical container runner — STUDY)
- deploy/queue-daemon/launch-queue-daemon.sh + ce-queue-daemon.service (MIRROR their pattern,
  incl. the inline Python lease supervisor with heartbeat cadence — that supervisor pattern IS
  the answer to lease-TTL-vs-long-items: 30s supervisor heartbeat << 300s TTL)

## Deliverables
1. validators/creator_engine_validator/conveyor_daemon_runner.py (NEW): main() + __main__,
   runnable as `python -m creator_engine_validator.conveyor_daemon_runner`.
   Env config (required, clear error on absence): CE_CONVEYOR_DAEMON_SEAT_PROBES (JSON array of
   {"seat_id","argv"}), CE_CONVEYOR_DAEMON_RUNTIME_ROOT, CE_CONVEYOR_DAEMON_DISCOVERY_STATE,
   GH_TOKEN, CE_DAEMON_LEASE_ROOT, and the receipt signing secret via
   CE_CONVEYOR_DAEMON_SIGNING_SECRET or CE_CONVEYOR_DAEMON_SIGNING_SECRET_FILE (CONTROLLER
   DECISION: file-based is the shadow-mode default; OpenBao wiring is the arming-step upgrade,
   NOT this PR; the secret must never enter the sandbox subprocess env),
   CE_CONVEYOR_DAEMON_REPO_ROOT (default /workspace/creator-engine).
   Optional w/ defaults: CE_CONVEYOR_DAEMON_INTERVAL_SECONDS=60, CE_CONVEYOR_DAEMON_ITERATIONS
   (N passes then exit, for tests/dry-run), CE_DAEMON_LEASE_TTL_SECONDS=300, CE_DAEMON_HOLDER_ID,
   CE_CONVEYOR_DAEMON_LEDGER_PATH, CE_CONVEYOR_DAEMON_VALIDATION_LEDGER_ROOT,
   CE_CONVEYOR_DAEMON_ACTIVE_WORK_LEDGER_ROOT.
   Seam construction: SeatProbeSpec list -> ConveyorSeatDiscoveryRunner(state_path, audit_sink);
   DaemonRuntimeRoots.from_root (0700 subdirs) -> DaemonPathAllocator; ValidationSandboxReceiptIssuer
   (non-empty secret validated); daemon_lease.acquire("conveyor-daemon", holder_id, ...);
   subprocess-backed git_runner + gh_runner (GH_TOKEN injected); now() ISO-8601; JSONL ledger_writer;
   ConveyorValidationLedgerBinding(controller_id="conveyor-daemon", lane_id="a1",
   claim_ref="ce-ops#388", repo_root=..., side_effect_ledger_root=..., active_work_ledger_root=...)
   — INJECT UNCONDITIONALLY (pre-empts slice 9 making it required; forward-compatible either
   merge order). Construction fails closed — never catch ConveyorDaemon.__init__ errors.
   Outer loop: run_once() + sleep(interval); CE_CONVEYOR_DAEMON_ITERATIONS bounds passes;
   SIGTERM -> graceful exit after current pass; lease.release() in finally.
2. deploy/conveyor-daemon/launch-conveyor-daemon.sh (NEW): mirror launch-queue-daemon.sh —
   container_adapter() -> run-daemon-container.sh conveyor-daemon; main_uncontained() via the
   inline lease supervisor (daemon name "conveyor-daemon"); validate_required_env; --health
   (process/container up + gh api user); --dry-run (CE_CONVEYOR_DAEMON_ITERATIONS=1).
   NOTE: the SHADOW evidence run will use the UNCONTAINED path on the host (probe argv needs
   ssh/docker/herdr reach the container does not mount); the containerized path is the
   canary/live form — both must work, deployment prerequisite (probe credential mounting) is
   documented in the launcher header comment, not solved here.
3. deploy/daemons/run-daemon-container.sh (MODIFY, minimal + backwards-compatible): fill the
   conveyor-daemon case with `python -m creator_engine_validator.conveyor_daemon_runner "$@"`
   and thread CE_CONVEYOR_DAEMON_* vars via add_env_if_present (mirror queue-daemon vars).
   Zero behavior change for the queue-daemon case.
4. deploy/conveyor-daemon/ce-conveyor-daemon.service (NEW): mirror ce-queue-daemon.service;
   Description "...(shadow mode)"; comment "# Shadow mode: deliberately disabled. Enable only
   after Operator-gated deployment flip."; NO [Install] section.
5. validators/tests/unit/test_conveyor_daemon_runner.py (NEW):
   - assembles daemon from env (fakes; CE_CONVEYOR_DAEMON_ITERATIONS=1)
   - refuses missing seat probes / missing signing secret BEFORE daemon construction
   - passes a non-None validation_ledger_binding to ConveyorDaemon (slice-9 pre-emption)
   - structural stop-line assertion: armed=True but NO approval-wall/reviewer/enqueue seam wired
6. .ce/changelog/ce-388-conveyor-harvest-daemon.md + carrier via carrier_gen API
   (write_carriers(base="origin/main"); rm build/ + *.egg-info first); carrier slug == branch.

## Allowed paths (exactly these)
deploy/conveyor-daemon/ce-conveyor-daemon.service · deploy/conveyor-daemon/launch-conveyor-daemon.sh ·
deploy/daemons/run-daemon-container.sh · validators/creator_engine_validator/conveyor_daemon_runner.py ·
validators/tests/unit/test_conveyor_daemon_runner.py · .ce/changelog/ce-388-conveyor-harvest-daemon.md ·
.ce/pr-manifests/ce-388-conveyor-harvest-daemon.md

## Novelty check (FIRST — semantic, against the deliverable seam)
Check whether an entrypoint that constructs ConveyorDaemon(armed=True) from live seat-probe
config already exists (conveyor_daemon_runner.py, launch-conveyor-daemon.sh, or a conveyor-daemon
CLI subcommand) under validators/creator_engine_validator/ or deploy/ on your origin/main.
run-daemon-container.sh's conveyor-daemon case currently DIES with "requires an explicit
in-container command" — that die-branch existing is EXPECTED, not evidence of prior work.
If a real entrypoint exists, report its path and signal BLOCKED already-landed.

## Preflight + signal (standing, ce-ops#303)
FULL `ce validate-pr` (TMPDIR=/var/tmp) GREEN one pass before commit-for-harvest. KNOWN CONTAINER
LIMITATION: if full validate-pr fails ONLY on this container's env (Python 3.14 contract /
missing tools), run focused green instead (test_conveyor_daemon_runner.py + test_daemon_lease.py
+ carrier/changelog checks), commit, signal READY with the env caveat.
Commit: `ce-ops#388: conveyor harvest daemon shadow-mode launcher + entrypoint`.
Signal EXACTLY: `READY-FOR-HARVEST ce-388-conveyor-harvest-daemon <full-40-hex-sha>`
or `BLOCKED ce-388-conveyor-harvest-daemon <reason>`.

## Done-report must include
Novelty-check evidence; stop-line confirmation (no approve/merge/enqueue code; no [Install]
section); the env-var contract table (required vs optional w/ defaults); any deviation from the
mirrored queue-daemon patterns with one-line rationale.
