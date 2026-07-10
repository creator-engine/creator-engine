# C5 CONTAINERIZED MERGE-GATE — EVIDENCE-PARITY ASSESSMENT — 2026-07-07 ~20:0xZ

Scope: ce-queue-daemon container (image creator-engine/ce-runtime:0.3.2-main, worktree
/home/cedev2/ce-daemon-main, BAO ttl ~24d) vs expected gate acts, since cutover
2026-07-07 ~16:1xZ (decision record: DECISIONS_20260707.md item 5). Evidence source:
`sudo docker logs ce-queue-daemon` (structured JSON; the host symlink
~/ce-wall-daemon-container.log is a stale 1-line pre-cutover launch artifact — its
lease-root ERROR predates the successful launch and is NOT a live failure).

## Quantitative evidence (passes 1–41, ~16:1xZ → ~20:0xZ)
- 41/41 passes complete, `failed_count=0` on every pass. Zero Tracebacks, zero 401s,
  zero lease errors in-container.
- Decision histogram, all consistent with expected gating rules:
  - skip/review_not_approved ×44 (#884 #886 pre-review; correct)
  - skip/draft_pr ×33 (#883 draft; correct — draft PRs never gate)
  - skip/governance_check_not_success ×7 (CI pending/red at decision time; correct fail-closed)
  - defer/approval_settle_pending ×4 (wall-settle discipline honored before enqueue)
  - defer/approval_capability_minted ×2 (container MINTED approval markers itself: #882, #885)
  - enqueue/eligible_enqueued ×9 (all for #882 head cf5dbd99a ×5 and #885 head 1a0303ea9 ×4;
    repeats are idempotent re-arms of `gh pr merge --auto` while CI ran, returncode 0 —
    benign, same code path as host daemon)

## Cycle count (the honest nuance)
- FULLY container-authored merge cycles (mint → settle-defer → enqueue → merged): **2**
  (#882, #885 — including #885, the Arad-send critical path).
- Merges completed under container custody with correct decisions throughout: **4**
  (#864, #878, #882, #885). #881 merged pre-cutover.
- Soak bar (decision 5) was "≥3 real queue cycles with evidence parity": MET on the
  custody count (4), one short on the strict container-authored count (2). The #488
  memory-layer PR (harvest in flight) supplies a 3rd container-authored cycle within
  hours and removes the ambiguity.

## Parity verdict
- Decisions vs expected acts: **PARITY — no deviation found.** Every decision class maps
  to the correct gate rule; both container-authored cycles produced correct merges; no
  act occurred that the host daemon would not have taken, and no expected act was missed.
- Known runtime deltas vs staged doc (both already adapted, decision 5): uid-10001 state
  ownership; interval via CE_QUEUE_DAEMON_INTERVAL_SECONDS instead of --loop.
- Rollback remains one line: `sudo docker stop ce-queue-daemon; bash ~/ce-wall-daemon-launch.sh`.

## Recommendation to Operator (promotion call is yours)
DECLARE parity met and promote C5 (retire host daemon from warm-standby to
rollback-only), EITHER now on the custody count, OR — zero-cost stricter option —
after the #488 PR completes the 3rd container-authored cycle (expected tonight).
Controller recommendation: the stricter option; nothing is blocked meanwhile and the
evidence becomes unambiguous.

## FINAL ADDENDUM 2026-07-08 ~00:xxZ — STRICT BAR MET
- 3rd fully container-authored merge cycle COMPLETE: PR #883 (mint → settle → enqueue at
  pass ~79 → merged, main c39ab688). Container-authored cycles: #882, #885, #883 = 3;
  more incoming tonight (#884/#886/#887 approved, enqueue on CI-green).
- Daemon still failed_count=0 through pass 80+. The recommendation's stricter option is
  now satisfied — the promotion call (retire host daemon warm-standby → rollback-only)
  is ready for Operator declaration with zero counting ambiguity.
