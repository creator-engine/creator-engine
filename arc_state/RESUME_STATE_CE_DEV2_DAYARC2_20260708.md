# RESUME STATE — CE-DEV-2 — 2026-07-08 morning — DAY-ARC-2 RATIFIED (pre-/clear checkpoint)

> READ ORDER: MEMORY.md → .ce/state/decisions/DECISIONS_20260708.md (items 1-10, ALL
> today: singleton+IaC rule, Option A rulings, C5 promotion, Ring-1 pre-acts, Arad
> apply, 0.3.4 cut, arc ratification, SIGNING GRANT, VPS sudo) → DECISIONS_20260707 →
> this file. Supersedes RESUME_STATE_CE_DEV2_NIGHT2_20260708T0xxx.md (night ledger
> preserved there: 13 merges, all set-pieces complete, board EMPTY at main 010ef3de).
> RULES: no `model` on pinned-role spawns; reviewer baseline = merge-base only;
> herdr/tmux Enter = SEPARATE send; watcher scripts die with session — REWRITE
> (board-watch: poll open-PR set+headRefOid+main head, exit on change; seat-watch:
> grep all THREE seat panes for 'READY ce-|BLOCKED[A-Z-]* ce-' w/ dedup file — dev-3
> via ssh dev1 docker exec, dev-4 local docker exec, dev-1 tmux; c5-watch: docker
> logs -f ce-queue-daemon, exit on failed_count>0|Traceback|401|lease|ERROR).
> Harvest-fast doctrine in force (runsc seats RAM-backed until relaunched on #891
> layout). Territory-check before every dispatch. ctx>45% = /clear.

## NEW AUTHORITY (verified this morning — use it)
- SIGNING: controller signs ce-root-v1 WITHOUT Operator per-act (passphrase verified;
  workers/standby NEVER sign). 0.3.4 is now fully controller-executable.
- VPS ROOT: ssh dev1 (=ce-dev-1) has passwordless sudo (verified) → ce-ops#184 tmpfs
  fix is controller-executable.
- GATE: containerized daemon IS the gate (C5 promotion DECLARED, decision 3); host
  daemon = rollback-only. Overnight-style gate authority continues per arc.

## DAY-ARC-2 LANES (all ratified, decision 8)
- A-1 ARAD: execute workflow-refresh apply via App lane (authorized) → then send
  blocks ONLY on Operator T4 pack + md-sources. Note: ARAD_SEND_READINESS file.
- A-2 C5 EXECUTION: document host-daemon demotion (rollback-only), update assessment;
  fold gate-redeploy into A-4's IaC unit.
- A-3 RING-1: dispatch launch-wired provenance unit (harness_matrix.py — cite
  decision 4 Operator authorization in PR); then LIVE governed `ce launch --harness
  codex` Ring-1 smoke → evidence packet → reassemble RING1_PROMOTION_PACKET →
  flip returns to Operator.
- A-4 OPTION A + IaC: (i) NEW unit: one-click IaC redeploy (VPS-runnable) for
  gate-daemon + materializer singletons — PRECONDITION for materializer arming
  (decision 1); (ii) Q2 credential check vs identity-registry SSOT (ce-ops:infra/
  identity-registry.yaml) → bring Operator the answer (lean: dedicated narrow App);
  (iii) then Option A impl slice 1 dispatchable (Q1/Q3/Q4 ruled, decision 2).
- A-5 0.3.4: full cut off CURRENT main (baseline v0.3.3; candidates file
  RELEASE_0_3_4_CANDIDATES_20260708.md; 35 PRs, zero missing changelogs) INCLUDING
  signing (decision 9). Follow ce-release-spec-signing-procedure playbook +
  release-cut-off-current-main memory; sha256-pinned files = release op.
- A-6 INTAKE (seat units, priority order): (1) seat-ready profile implementation
  (#892 design on main — new successor profile, NOT contained-seat mutation);
  (2) fleet-parity: seat image rebuild + ssh-keygen (dev-3 gap), dev-4 egress-broker
  deploy on DGX + self-push canaries both seats; (3) IaC redeploy unit (A-4i);
  (4) launch-wired provenance (A-3); (5) broker v1 implementation slice 1 (#884
  design on main) = the controller-containment critical path (accelerator per
  decision 8). Also queued: ce-ops#184 execution (controller-direct, VPS root).

## SEATS AT CHECKPOINT
All idle-warm, zero in-flight units, board EMPTY. dev-1 (self-push, tmux
ce-dev1-orchestrator:2.0); dev-3 (relaunched, broker socket live, ssh-keygen still
missing, 2× zero-repair harvests); dev-4 (strongest, commit-only until broker
deploy). Codex standby alive (tmux ce-controller; can't reach ce takeover from
release-branch checkout — ce-ops#502). Root checkout parked on ce-release-0.3.1-rc2
(stale lineage; do not disturb without context).

## FLEET ANSWERS GIVEN TO OPERATOR (decision 8)
Seats parity ~Jul 10-11 (2-3 arcs). Daemons containerized ~1 week. Controllers
containment/parity = #496/#498 (T1 Aug 11 / T2 Aug 31); accelerator = broker v1 lane.

## ⏸️ AWAITING-OPERATOR (only 3 left!)
1. Arad T4 pack + md-sources decision (send-ready otherwise).
2. Option A Q2 ratification after controller brings the identity-registry answer.
3. Nitzan D6 answers (their own timebox) + Ring-1 flip (returns WITH smoke evidence).

## FIRST MOVES ON RESUME
1. Board check + re-arm 3 watchers (rewrite scripts per RULES above).
2. Dispatch A-6 intake batch (territory-check first; briefs via pointer+SHA).
3. Controller-direct: A-1 Arad apply staging, A-5 0.3.4 staging, #184 tmpfs fix.
4. Q2 identity-registry check.
EOF
cat /home/cedev2/creator-engine/.ce/state/research/RESUME_STATE_CE_DEV2_DAYARC2_20260708.md | ssh dev1 'cat > ~/creator-engine-state-mirror/RESUME_STATE_CE_DEV2_DAYARC2_20260708.md' && echo CHECKPOINT-DUAL-WRITTEN