# RESUME STATE — CE-DEV-2 — 2026-07-10 ~16:5xZ — STRANGELOOP2E (PRE-DRILL CHECKPOINT)
# Supersedes 2D. Written by the Claude face MOMENTS BEFORE the N-2 dead-man drill self-kill.
# ⚓ ARC ANCHOR = .ce/state/research/ARC_STRANGELOOP_NIGHT3_MANDATE_20260710.md — RATIFIED.
#   Delegate-operator (this mandate ONLY) = DGX supervising session, via pane messages.
#   8 HARD STOPS enumerated in the mandate — read it before ANY act. Operator returns ~10h.
# The AUTHORITATIVE in-flight table lives in CONTINUITY_DRILL_EVIDENCE_20260710.md (same dir,
#   bottom section) — checkpoint + evidence file together are the full resume packet.

## SCOREBOARD (since 2D, ~4.5h)
- MERGED: #956 (gate hotfix: signed-pins parse + malformed-fixtures scope — was red-lighting
  EVERY validate), #947 (F-1 storage admission, conflict-resolved + round-2), #957 (523b JIT
  deflake), #958 (materializer CAS-push, 3 arming-slice advisory notes recorded in review).
- #959 (materializer deploy-unit) APPROVED + automerge armed at review time — VERIFY LANDED.
- Wave remaining in pipeline: n15b (validating), ce-529, terra-flip(!relaunch-safety), n15a,
  523c, custody-runbook, n1s2, ce239, f1s2. Loop: green→auto-push+PR→review→approve→merge.
- Fleet delivered today (harvested, in queue): dev-4 = n15a, n1s2 (acting review chain), f1s2;
  dev-3 = 523c, custody-runbook. Seats NOW: dev-3=453b, dev-4=n11s1, dev-1=n8-IaC (self-push).
- DRILL: fire condition (#947+#950+#957 merged) MET — this checkpoint is step 1 of the fire
  sequence. Harder variant ratified: everything above = standby INHERITANCE.

## HARD-WON RULES (2D's eight still stand; new since)
9. Patching a script under a live long-running process requires RESTARTING the process (bash
   parses at start — the on-disk fix never reaches the running daemon). Singleton+IaC redeploy
   rule applies to controller automation. (#956 body bug repeat; runner restarted.)
10. Monitor coverage must include FAILURE states — a PR-state watch that only sees OPEN/MERGED
   sits silent through a CI red (70-min stall). N-15a lands the mechanical fix; until then run
   the hourly PR-limbo check the Operator advised at sign-out.
11. No backticks/$() in pane messages (shell-substitutes before delivery); signal watchers must
   anchor on the terminal bullet prefix or brief echoes false-fire. (In dispatch-mechanics memory.)
12. Seat structural BLOCKED escalations are often RIGHT (dev-4 ×2 today: unreachable wiring seam,
   lane-launch context gap; dev-1 ×1: inert-IaC boundary) — verify, then AMEND THE BRIEF in
   place (append AMENDMENT section, re-sha, re-point) rather than overriding.
13. Verify-not-landed before every dispatch: N-3 dualformat was ALREADY MERGED (dead dispatch
   avoided); N-11 slice 1 partially existed (brief rescoped to the real gap).

## MECHANICS QUICK-CARD (details in the evidence-file table)
- Pipeline: /var/tmp/ce-pipeline.sh {harvest|queue|runner|push}; queue list+lock in /var/tmp;
  q-logs /var/tmp/q-<branch>.log; runner survives face death; on-disk script has push
  lease-fallback the RUNNING runner lacks (restart only at idle gap).
- Approve as ce-dev-2 PAT; merge via `gh pr merge N --auto` (no --squash). PUSH→REVIEW→APPROVE.
- Seat drive/read: herdr INSIDE containers, -e HERDR_SOCKET_PATH=/run/creator-engine/herdr/
  herdr.sock, dev-3 user ce-dev-3 local, dev-4 user cedev4 via DGX ssh key. Pointer+SHA briefs.
- Claims/briefs: .ce/claims/ + .ce/briefs/ (this repo). Fleet signals: .ce/state/fleet-signals.log.

## AWAITING-OPERATOR (morning queue, priority order per mandate)
Materializer ARMING decision (#958/#959 landed the mechanics + IaC; ADR-0015 ratified; three
arming-slice advisory notes in #958's review) · N-14 dev-1 containment GO · gate redeploy +
storage-reaper/seat-watch deploys (task board) · release-op ce-469 (non-delegable) · canary
terra readout + xhigh/Sol · PV design #524 · STRANGELOOP-3 ratification. Nitzan D6 standing.
