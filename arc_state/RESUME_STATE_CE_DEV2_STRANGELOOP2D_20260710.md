# RESUME STATE — CE-DEV-2 — 2026-07-10 ~12:3x UTC — STRANGELOOP2D
# Supersedes 2C. Claude face (session dbe6fa03, --dangerously-skip-permissions, relaunch via
# ~/resume-controller.sh). Codex successor STANDBY (tmux ce-dev2-controller:codex-controller).
# ARC = STRANGELOOP-2 + ratified supplement (N-1..N-15, N-15a/b, N-2-DRILL) + GPT-5.6 routing.

## SCOREBOARD (since the 2026-07-09 emergency migration, ~19h)
- **24 PRs MERGED.** Open: #955 (ADR, approved, in queue), #947 (F-1, approved, in queue).
- Stale tickets closed with evidence: 15. New tickets filed: 522 523 524 525 526 527 528 529.
- Storage incidents: 4, all root-caused + fixed (F-1 in queue = product fix).
- Self-push gaps: ZERO (dev-4 lane live, canary-proven; dev-3/dev-1 lanes pre-existing).
- Flake campaign: sentinel (#950 merged), JIT (ce-523b queued) → suite flake surface ≈ 0.

## FLEET (all: codex 0.144.1, gpt-5.6-terra high — Operator-accelerated flip, canary running)
- dev-3 (ce-vps-codex, LOCAL, w1:p1): idle-ready, ctx 83% left. Last: N-15b delivered.
- dev-4 (ce-dgx-codex, DGX via ssh key, w1:p1 — NOT w5): building N-15a. ctx 87% left.
- dev-1 (peer, tmux ce-dev1-orchestrator:2.0): terra, thread resumed; #930 merged; free.
- CANARY LEDGER OWED: first-READY green rate / review bounces / corrective round-trips vs the
  5.5 baseline. Observed terra datapoints: dev-3 premature-signal ×2 (uncommitted branch),
  dev-4 clean multi-unit batches. xhigh decision DEFERRED until readout.

## PIPELINE (mechanized — /var/tmp/ce-pipeline.sh: harvest|queue|runner|push)
Runner detached, serialized, dual-FS disk gates, AUTO-REBASE onto main before each validate,
auto-push+PR on green. Queue now: ce-529, ce239, cas-push, 523b-deflake, deploy-unit, n15b
(+ terra-flip in slot). Verdict logs /var/tmp/q-<branch>.log. Monitors: biup0bc5l (segments),
b2ahw45ve (dev-3 signals), b71ajzx18 (drain watch v3, one-retry flake policy).
MY LOOP PER BRANCH: spawn reviewer → adjudicate → **PUSH BEFORE APPROVE** → merge --auto.

## HARD-WON RULES (all persisted to memory; violating them cost hours today)
1. `push → review → approve` — approving before a fix-push head-invalidates the approval.
2. Pipeline/automation output must self-validate against the gates it feeds (my body-assembler
   read changelogs from the main repo root, not the worktree → EIGHT PRs uniformly red on G5).
3. Decision records name ROLES, never seats (peer-authority VAL-PA-SELF-APPROVAL + public-doc
   confidentiality both fire; ce-runtime-architect/ce-gate-architect are the pattern).
4. Reruns replay STALE event payloads — re-EVENT (close/reopen), don't re-run, when a gate
   reads the PR body.
5. Never the bare `sonnet` Agent alias (= Sonnet 5, BANNED). Pinned roles / opus / haiku only.
6. Base pins in briefs: "<sha> OR LATER" during active landing; hard pin only for release cuts.
7. Seat "done" ≠ committed — verify branch head ≠ base before harvesting (2 false signals).
8. Post-relaunch seats lose PATH: briefs must use /workspace/creator-engine/.venv/bin/ce.

## IMMEDIATE NEXT (ordered)
1. **N-2 DRILL** (Operator-ordered, drain reached): dead-man script staged at
   /var/tmp/drill-deadman.sh; evidence protocol + success criteria pre-registered at
   .ce/state/research/CONTINUITY_DRILL_EVIDENCE_20260710.md. Execute: stamp drill_armed →
   `setsid nohup bash /var/tmp/drill-deadman.sh <my-pid> &` → SIGTERM own claude PID.
   Standby resumes from durable state; revive via ~/resume-controller.sh for the audit.
2. Task #15 gate redeploy: ff ~/ce-daemon-main, EDIT DROP-IN FIRST (remove CE_DAEMON_LOG_DIR,
   add CE_DAEMON_LIVENESS_STATE_PATH), then redeploy-singleton.sh --daemon queue-daemon.
   Also deploy: storage-reaper timer, seat-watch (slices 1+2 together).
3. Slice (c) dispatch (App-key custody runbook) — unblocked by #955's merge (ADR ratified:
   status accepted, chmod735, quorum n1_solo).
4. N-14 dev-1 containment (last containment-mandate item).
5. My release-op (non-delegable): ce-469 shim guard + llms-install CE_INSTALL_ROOT/agent-usage
   + re-sign per ce-release-spec-signing-procedure.
6. PV design mandate (ce-ops#524) after the daemon wave.

## AWAITING-OPERATOR
Nitzan D6 (standing). Nothing else blocks.
