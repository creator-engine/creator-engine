# CE-388 Conveyor Discovery Runner — First Live Shadow Run (Evidence Record)
Date: 2026-07-04T09:19Z · Runner head: b9fe1dfb (PR #775 merged 09:15:42Z) · Verifier: read-only verification worker (Haiku), controller-banked.

## Verdict: SHADOW MODE PROVEN — READY FOR ARMING (auto-PR-open milestone next)

## Setup
ConveyorSeatDiscoveryRunner with 3 real SeatProbeSpecs:
- dev-1: ssh dev1 tmux capture-pane -t ce-dev1-orchestrator:2.0 -p
- dev-3: ssh dev1 sudo docker exec (HERDR_SOCKET_PATH) ce-vps-codex herdr pane read w1:p1
- dev-4: sudo docker exec (HERDR_SOCKET_PATH) ce-dgx-codex herdr pane read w1:p1
state_path=scratch, audit_sink=enabled. Zero mutations to repo or seats.

## Results vs ground truth (all three seats mid-build, no real signals)
| Seat | Probe | Verdict | Notes |
|---|---|---|---|
| dev-1 | OK | NO SIGNAL | 1 READY-FOR-HARVEST token in pane (controller nudge prose) correctly rejected as `non_signal_ready_echo` |
| dev-3 | OK | NO SIGNAL | mid ce-437 rework validate-pr |
| dev-4 | OK | NO SIGNAL | mid S3 build |

Payloads discovered: 0 (correct). False positives: 0. False negatives: 0.

## Capability matrix — all OK
Remote ssh probe · contained docker-exec probe (both VPS and DGX) · signal parse (8/8 pattern tests: bullet/dash/bare forms, placeholder-SHA reject, diff-echo reject, slug-mismatch reject, prose reject, REWORK-N tags) · dedup via atomic temp+rename state · audit sink records every rejection reason.

## Notable
The live false-positive rejection fired on REAL noise (controller's own dispatch nudge echoed on dev-1's pane) — the exact failure class that produced 2 false seat-signals on 2026-07-04 morning, now provably encoded.

## Residuals for arming (not shadow gaps)
- Armed-mode payload schema + anti-injection checks already unit-tested.
- Daemon working-dir setup lives in conveyor_daemon.py (next leg's scope).
- Next milestone per DAYARC mandate A1: shadow-mode daemon that AUTO-OPENS PR from a READY seat (no auto-merge). Appetite note: Operator called one-day-arc conservative → extend within arc without re-asking.
