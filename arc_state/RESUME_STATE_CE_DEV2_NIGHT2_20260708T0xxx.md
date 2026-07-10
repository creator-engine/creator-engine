# RESUME STATE — CE-DEV-2 — 2026-07-08 ~0x:xxZ — night-arc-2 mid-arc delta

> READ ORDER: MEMORY.md → DECISIONS_20260707.md (items 1-7) →
> NIGHTARC_MANDATE_CE_DEV2_20260707_NIGHT2.md (RATIFIED, overnight gate authority
> explicit) → this file. Supersedes RESUME_STATE_CE_DEV2_DAYARC_20260707T18xxZ.
> Standing rules unchanged (no model on pinned roles; merge-base reviewer baselines;
> herdr Enter separate; watcher scripts session-mortal — specs in scratchpad
> board_watch.sh/seat_watch.sh/c5_watch.sh pattern, rewrite from ce-ops#497).

## NIGHT LEDGER (so far)
- MERGED tonight: #883 (runbook, un-drafted+gated), #884 (broker design), #886
  (bottom-out design), #887 (NanoClaw seam, T0 bar met), + #885 pre-arc = journey
  to main. C5 authored cycles ≥6, failed_count=0 through 80+ passes.
- C5 PROMOTION EVIDENCE COMPLETE: C5_PARITY_ASSESSMENT_20260707.md + FINAL ADDENDUM
  (strict bar met). Promotion declaration = Operator (morning queue #2).
- APPROVED, queuing: #888 (memory-layer, r2-verified; N1-N3 non-blocking follow-ups
  noted on PR), #890 (dev-3 follow-ups batch, clean sweep).
- IN CYCLE: #889 Option A design r3 (dev-4 Working: two surgical edits — #888
  prerequisite correction + decision/lesson payload mapping; ALL else confirmed
  resolved, do not re-litigate).
- dev-3 OOM INCIDENT closed: root cause = dev-1's 3×-n-auto suites filling 16G tmpfs
  (=RAM); ticketed ce-ops#500 (4 slices) + #184 root fix (Operator); memory
  ce-runsc-seat-worktree-in-memory-loss; seat relaunched canonically (broker env now
  set; ssh-keygen still missing). ce-ops#499 = seat-side preflight gap (filed; #890
  = first zero-repair harvest datapoint).

## SEATS
- dev-1 (self-push): U1 ce-500-launcher-durability (launcher scripts ONLY —
  validators/ forbidden) + U2 ce-499-seat-preflight-design (design-only). Brief
  BRIEF_dev1_restock_20260707T23.md. tmux Enter must be a SEPARATE send-keys.
- dev-3 (relaunched, fresh): idle post-#890. QUEUED RESTOCK: #888 N1-N3 hygiene batch
  (newest-resume-state sort semantics + touch() test pin + digest reuse — see #888
  approval comment) — dispatch AFTER #888 merges (same files).
- dev-4: Working #889 round-3 (BRIEF_dev4_889_round3_20260708.md). After: free for
  intake; #889 implementation stays BLOCKED on 4 Operator questions.

## SET-PIECES REMAINING (N-C/N-E)
- D4 Ring-1 packet assembly: NOT started.
- D3 shadow canary (dry_run second daemon): NOT started.
- D6 drill #1: standby VERIFIED ALIVE (tmux ce-controller, 61% ctx, authed) — drill
  needs #874 harness no-gate-authority mode check first.
- 0.3.4 assemble-only: NOT started (candidate list = today's 13 + tonight's merges).

## ⏸️ MORNING OPERATOR QUEUE — mandate file items 1-7 (Arad apply first, C5
promotion, Option A 4-question ruling, Ring-1 flip, 0.3.4 co-sign, Nitzan, #184).

## RE-ARM ON RESUME
Board check (open PRs #888/#889/#890 states + main head) → re-arm board/seat/C5
watchers (scripts in this session's scratchpad die) → sweep seat panes → continue
N-A drain, then set-pieces.

## DELTA ~0x:xxZ+2 — BOARD DRAINED
- Merged additionally: #891 (launcher durability — OOM work-loss fix live at next relaunches).
- #889 (Option A design, r3) + #892 (seat-ready preflight design, r2) APPROVED, queuing.
- Board = zero awaiting-review. C5 authored cycles ≥9, failed_count=0 throughout.
- In build: dev-1 ce-891-hygiene-pair (XS); dev-3 ce-888-hygiene-n1n3 (tiny); dev-4 idle-warm.
- NEXT: N-C set-pieces — D4 Ring-1 packet (assembly launched), D3 dry-run canary, D6 drill
  (standby verified alive earlier). Then N-E 0.3.4 assemble-only.

## D4 OUTCOME (~0x:xxZ+3)
- Packet: .ce/state/research/RING1_PROMOTION_PACKET_20260708.md. HONEST tally 1 MET /
  5 PARTIAL / 7 MISSING of 13 criteria. Ring-1 flip is NOT a tonight act.
- Two pre-acts before the flip (morning queue item updated): (1) Operator updates
  launch-wired provenance in harness_matrix.py (currently hardcoded "deferred pending
  containment acceptance"); (2) a live governed `ce launch --harness codex` Ring-1
  smoke that writes the evidence packet (.ce/state/controller-evidence/ is empty —
  no packet has ever been written on this host).

## D3 CANARY LIVE (~0x:xxZ+4)
- ce-queue-canary running: DIRECT daemon invocation (bypasses launcher's hardwired
  openbao backend flag — that flag turns dormant into configured_backend_without_secret
  refusal; canary runs with NO approval-wall backend → wall DORMANT, no marker issuer).
- Zero authority: dry-run mode, wall dormant, GH token = App installation token
  downscoped to contents:read+pull_requests:read (push=False verified), expires ~1h.
- Isolated state /home/cedev2/ce-canary-state; shares /home/cedev2/ce-daemon-main
  worktree READ-ONLY. First pass clean, decision parity plausible vs live.
- Parity comparison due when the 45-min window timer fires: compare daemon_decision
  (pr_number+head_sha+status+reason) streams, then `sudo docker rm -f ce-queue-canary`.
- LEARNING for the D3 report: the launcher needs a first-class canary/dormant mode
  (env flag to omit the secret-backend flags) — ticket with the D3 results.

## ═══ NIGHT-ARC FINAL DELTA (pre-dawn) — ALL LANES COMPLETE ═══
- N-A: 12 merges tonight (#883 884 885* 886 887 888 889 890 891 892 893 +#885 day),
  every one independently strict-reviewed (several through 2-3 remediation rounds),
  BOARD EMPTY. C5 authored cycles ≥12, failed_count=0 throughout.
- N-B: C5 promotion package COMPLETE (assessment + strict-bar addendum).
- N-C: D4 packet (1 MET/5 PARTIAL/7 MISSING — flip needs 2 pre-acts); D3 canary
  GREEN (report D3_SHADOW_CANARY_REPORT_20260708.md; gap→ce-ops#501); D6 drill #1
  COMPLETE-FAILED-USEFULLY (report D6_DRILL1_REPORT_20260708.md; standby can't reach
  ce takeover from release-branch checkout → ce-ops#502; harness GREEN on main with
  both of tonight's hydration actions present).
- N-E: 0.3.4 candidates assembled (RELEASE_0_3_4_CANDIDATES_20260708.md): baseline
  v0.3.3 (#857, 2026-07-06), 35 PRs (14 feat/5 fix/2 docs/7 design/7 infra), ZERO
  missing changelogs. Cut + ce-root-v1 co-sign = Operator ceremony.
- Tickets born tonight: ce-ops#499 (seat preflight; design MERGED as #892), #500
  (OOM/durability; launcher fix MERGED as #891), #501 (canary launcher mode), #502
  (standby takeover surface).
- Seats at dawn: dev-3 building ce-888-hygiene-n1n3 (harvest on READY); dev-1/dev-4
  idle warm; next natural intake = seat-ready profile implementation (design now on
  main via #892) + Option A implementation AFTER the Operator 4-question ruling.
- NOTE: root checkout still parked on ce-release-0.3.1-rc2 (stale lineage — real
  baseline is v0.3.3); relates to #502; do not "fix" without Operator context.

## ⏸️ MORNING OPERATOR QUEUE (final): 1 Arad apply; 2 C5 promotion (package ready);
3 Option A 4-question ruling; 4 Ring-1: two pre-acts then flip; 5 0.3.4 cut+co-sign
(35 candidates ready); 6 Nitzan D6 answers + #474; 7 ce-ops#184 tmpfs root fix.
- POST-FINAL: #894 (ce-888 hygiene N1-N3, dev-3's 2nd zero-repair harvest) APPROVED →
  13th night merge MERGED 00:43Z (after one unrelated CI flake — test_jit_credential_broker BrokenPipe, single re-run greened; ticket only if it recurs). Seat-watch script gap fixed (dev-3 pane now covered).
  All seats idle-warm at dawn; conveyor clean.
