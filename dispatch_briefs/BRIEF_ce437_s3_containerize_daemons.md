# SEED BRIEF — ce-437 slice 3: containerize governance daemons + singleton-lease gate

Ticket: ce-ops#437 (two-plane OS architecture, slice 3). You cannot read the ticket; this brief is
self-contained. In-repo context you MUST read first:
- docs/decisions/ADR-0014-two-plane-os-architecture.md (ratified: portable Python control plane +
  ONE canonical Linux container runtime image; systemd = thin adapter only; container-first for
  ALL forms)
- deploy/queue-daemon/ (current host-side packaging of the approval-wall queue daemon:
  ce-queue-daemon.service + launch-queue-daemon.sh + RELOCATION.md)
- validators/creator_engine_validator/conveyor_daemon.py (daemon core on main, DISARMED by default)

Role: implementer (foreman fan-out allowed). Seat: dev-4. Worktree: /var/tmp/wt-ce437s3
(branch ce-437-s3-containerize-daemons off your origin/main; controller rebases at harvest).

## Goal
The governance daemons (queue/approval-wall daemon, conveyor daemon) currently run host-side via
ad-hoc launch scripts + systemd units. Slice 3 makes them run inside the canonical runtime
container, with a SINGLETON LEASE gate so at most one live instance of a given daemon can hold
its arming lease at a time — across restarts, duplicate launches, and host+container overlap.

## Deliverables
1. NEW module validators/creator_engine_validator/daemon_lease.py — filesystem lease under a
   configurable state root (default .ce/state/daemon-leases/<daemon-name>.lease):
   - acquire(daemon_name, holder_id): atomic create (O_EXCL semantics); refuse if a live lease
     exists; a stale lease (holder process dead / heartbeat older than TTL) may be reclaimed only
     with an explicit audited takeover record, never silently.
   - release(): idempotent; heartbeat(): updates mtime/payload.
   - FAIL-CLOSED: any lease-state ambiguity (unreadable/malformed lease file, state root missing)
     → daemon must NOT arm; plain-text reason surfaced. Lease payload is data-only (JSON:
     holder_id, pid, host, acquired_at, heartbeat_at) — nothing from it is ever executed.
2. Wire the gate into conveyor_daemon.py startup: no lease → refuse to enter armed mode
   (disarmed/report-only paths may run leaseless). DO NOT change any arming defaults — daemon
   stays disarmed-by-default; this slice only ADDS the lease requirement to the armed path.
3. NEW deploy/daemons/ container packaging: Dockerfile (or reuse/extend the canonical image per
   ADR-0014 — prefer referencing the existing canonical image over a new base), run script that
   is ENGINE-AGNOSTIC (docker or podman via $CE_CONTAINER_ENGINE, no hardcoded engine), mounting
   only what the daemon needs (state root, repo checkout read path, token file path as documented
   variables — no secrets baked into images or scripts).
4. Convert deploy/queue-daemon/ce-queue-daemon.service into a thin adapter that invokes the
   containerized run script (systemd = adapter only, per ADR). Keep the old direct-launch path
   working behind an explicit CE_DAEMON_UNCONTAINED=1 escape hatch documented in RELOCATION.md.
5. Tests (validators/tests/unit/): test_daemon_lease.py covering at minimum — acquire/refuse on
   live lease; reclaim-only-with-takeover-record on stale lease; fail-closed on malformed lease
   file AND on missing state root; release idempotency; two same-second acquirers → exactly one
   winner. Plus conveyor_daemon armed-path test: armed start without lease is refused. No test
   may require docker/podman at runtime — use injected runner/fake-fs seams.
6. Changelog fragment .ce/changelog/ce-437-s3-containerize-daemons.md.

## Stop line (allowed paths — nothing else)
deploy/daemons/** (new) · deploy/queue-daemon/** · validators/creator_engine_validator/daemon_lease.py (new)
· validators/creator_engine_validator/conveyor_daemon.py (minimal lease wiring only)
· validators/tests/unit/test_daemon_lease.py (new) · validators/tests/unit/test_conveyor_daemon.py (extend)
· .ce/changelog/ce-437-s3-containerize-daemons.md
FORBIDDEN (in-flight territory): container_launcher.py, worker_runtime.py, conveyor_discovery.py,
ce_cli.py, v3_cli.py, checks/**, docs/install.sh, docs/downloads/**, README.md, surfaces/**.
No new top-level `ce` CLI group (docs-reconciliation coupling). No secrets anywhere.

## Obligations
- Run the FULL local validator preflight (`ce validate-pr`, CI-parity) before commit-for-harvest;
  do not discover gates via CI. Use `.venv/bin/python -m ...` (no activate in your venv).
- Commit everything; do NOT push (no push auth). Then print the signal EXACTLY:
  READY-FOR-HARVEST ce-437-s3-containerize-daemons <full-40-hex-commit-sha>
  (real 40-hex SHA — never the placeholder; controller rejects placeholders)
- If genuinely blocked, print: BLOCKED ce-437-s3-containerize-daemons <one-line reason>
