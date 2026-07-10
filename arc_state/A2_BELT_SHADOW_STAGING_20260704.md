# A2 Belt Shadow-Arming — SHADOW LIVE + FIRST EVIDENCE GREEN (2026-07-04, enabled ~10:12Z)

## Status: SHADOW MILESTONE COMPLETE. Both daemons ACTIVE in --dry-run on dev-1; 3 clean passes each.
Enable gate was satisfied 10:0xZ: dev-1 pushed 8b (PR #777) → governed cev3 upgrade 0.2.0→0.3.1 in the installer's bootstrap venv (~/.local/share/creator-engine/bootstrap/venv) from the hash-verified signed wheelset (7/7 SHA256SUMS OK, --no-index) → enable-linger + enable --now → --dry-run confirmed in effective ExecStart of BOTH units (--apply absent from review-pickup).

## Shadow-run evidence (first 3 passes, ~10:12-10:19Z)
- integrator (queue-daemon --dry-run): every pass logs dry_run=true; decisions INDEPENDENTLY MATCH the live DGX wall daemon's real timeline on #776 (skip governance_check_not_success → defer approval_settle_pending → status=enqueue reason=eligible_dry_run with full 16-path carrier set) while executing nothing. Skips correct on #772/#774/#777/#778 (review_not_approved).
- review-pickup (--dry-run, --apply stripped): routing decisions logged (routed #777/#778 → ce-dev-2, requested=false because review already requested — correct dedupe), inbox .ce/state/controller-inbox/awaiting-review.json written with structured records (controller_reviewer, ci_state per PR).
- Benign notes: unit-file Documentation=./README.md invalid-URL warning (cosmetic, repo unit); "approval_wall: not armed" evidence on dev-1 (expected — no wall secrets there; dry-run makes the non-wall fallback safe). Both feed the canary precondition list below.
- Raw journal excerpt: session task bx29vztvv output (integrator passes 1-3 + review-pickup passes 1-3 + inbox head).

## Why gated
dev-1 host cev3 = 0.2.0+4f4bd35e — has NO `--dry-run` on queue-daemon/review-pickup (verified via --help probe). release/v0.3.1 HAS both flags (v3_cli.py:4180 review-pickup, :4528 queue-daemon — verified via git show on the tag). Upgrading a controller host's toolchain mid-build is refused; 8b completion is the gate.

## Hold-scope ruling (controller, evidence-backed)
ce-ops#410 arming blockers (allocation receipts, credentialless sandbox, credential separation) all target conveyor_daemon/conveyor.py ARMED mode. Gate-belt daemons in --dry-run mutate nothing; DAYARC mandate A2 explicitly ratifies shadow→canary→live for these two. Shadow proceeds; canary/live flip re-checks the hold + needs the credential/identity decision below.

## Staged on dev-1 (user ce-dev-1)
- ~/.config/systemd/user/ce-integrator-daemon.service + ce-review-pickup-daemon.service (copied from main-head b9fe1dfb deploy/systemd/ — checked-in units are live-shape and CI-asserted by test_gate_daemons_systemd.py; NEVER add --dry-run to repo copies).
- Drop-ins <unit>.d/shadow.conf: PATH+=~/.local/bin (cev3 location), WorkingDirectory=/home/ce-dev-1/creator-engine (repo unit says /workspace/... container path), ExecStart reset + --dry-run appended; review-pickup additionally has --apply STRIPPED (dry-run overrides apply anyway; belt-and-braces).
- ~/.config/creator-engine/gate-daemons.env (600): CE_GATE_REPO=creator-engine/creator-engine, CE_GATE_AUTHORIZED_REVIEWERS=ce-dev-2, GH_TOKEN/CE_PICKUP_TOKEN = dev-1's OWN gh token (deliberate: ce-dev-2 merge-gate PAT NOT copied cross-host for shadow; proper OpenBao-pointer credential wiring = canary precondition).

## Remaining enable sequence (after 8b + cev3 0.3.1 upgrade)
sudo loginctl enable-linger ce-dev-1 (Linger=no today) · systemctl --user daemon-reload · enable --now BOTH units · verify --dry-run in `systemctl --user show -p ExecStart` · watch ≥2 passes (interval 120s) in `journalctl --user -u ce-<unit>` for daemon_pass_start/complete + per-PR decisions · inspect .ce/state/controller-inbox/awaiting-review.json (written even in dry-run).
Rollback: systemctl --user disable --now both; deeper: rm drop-in + daemon-reload NEVER (that flips to live-shape) — rm the whole unit files instead.

## Canary/live preconditions (banked for the flip decision)
1. ce-ops#410 hold re-check (integrator Track B slices status). 2. Credential/identity: review-pickup runs --identity ce-dev-2 — needs the real approval-wall/OpenBao wiring, not dev-1's read token. 3. DGX wall daemon (PID 648947 here) already owns live merges — dev-1 belt canary must not double-drive gh pr merge --auto (idempotent but noisy); sequencing decision needed. 4. Missing runbook now tracked (ops_triage worker filed/commented — see its report).

Research SSOT for this staging: architect brief in session a8c67c5c (file paths + line refs for every claim above).
