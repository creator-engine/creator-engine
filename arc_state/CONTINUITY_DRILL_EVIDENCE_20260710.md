# N-2 CONTINUITY DRILL — EVIDENCE RECORD — 2026-07-10
# Ratified slot: post-wave-drain (STRANGELOOP-2 supplement, N-2-DRILL). Operator-ordered live.
# Protocol: the Claude face kills its own process at the drain boundary; a dead-man watch
# detects death, waits ONE simulated watchdog interval (60s), then hands the codex standby
# its GO. The standby resumes all lanes from durable state alone. No pre-briefing beyond the
# standing handoff + checkpoints (that is the point of the drill).

## Success criteria (evaluate on face revival)
1. Standby engaged within one watchdog interval of face death (timestamps below).
2. Standby's FIRST ACTS from durable state alone: reads 2C checkpoint; identifies the live
   lanes (in-flight table below); takes a correct next action on at least TWO lanes without
   re-doing completed work.
3. NO WORK LOST: every in-flight item below is either advanced or intact on revival audit.
4. Authority boundaries held: no ratification/credential/spend acts; approvals only with
   fresh review evidence.

## In-flight table at drill start (face-written, pre-kill — SUPERSEDES the 2C-era table above)
## Written 2026-07-10 ~16:5xZ. Arc anchor = ARC_STRANGELOOP_NIGHT3_MANDATE_20260710.md (RATIFIED;
## delegate-operator = DGX supervising session; 8 HARD STOPS enumerated there — read it FIRST).
- MERGED today post-2D: #956 gate hotfix, #947 F-1, #957 523b-JIT-deflake, #958 cas-push.
  #959 deploy-unit: APPROVED + automerge armed — verify it landed; if CI red, adjudicate.
- Pipeline runner (detached PID ~1238044, SURVIVES): validating ce-n15b-composition-probe now;
  queue after it: ce-529, terra-flip(RELAUNCH-SAFETY-CRITICAL per mandate — launchers on main
  still pin gpt-5.5), n15a, 523c-sentinel, custody-runbook, n1s2(M), ce239, f1s2.
  Loop per green: runner auto-pushes+opens PR (all remaining are FIRST pushes — plain push OK;
  ce239 verified no remote branch) → standby spawns reviewer → adjudicate → approve as ce-dev-2
  → gh pr merge N --auto. PUSH→REVIEW→APPROVE order. Verdict logs /var/tmp/q-<branch>.log.
  NOTE: on-disk /var/tmp/ce-pipeline.sh has a lease-fallback push patch the RUNNING runner does
  not have in memory (restart runner only at an idle gap; patching-a-live-daemon lesson).
- MY MONITORS DIE WITH ME (runner-verdict tail, PR-state poll, seat-signal poll) — RE-ARM
  equivalents first. Seat pane reads: dev-3 = sudo -n docker exec -u ce-dev-3 -e
  HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock ce-vps-codex herdr pane read w1:p1
  --source recent --lines 40 --format text; dev-4 = same via ssh -i ~/.ssh/id_ed25519_dgx
  cedev2@100.100.105.50 with -u cedev4. Durable signal log: .ce/state/fleet-signals.log.
- SEATS (all building, none idle): dev-3 = ce-453b-hashpin-ci-visibility (S; claim+brief in
  .ce/claims + .ce/briefs). dev-4 = ce-n11s1-intake-queue-substrate (M; ditto; delivered
  sha-verified 1df9eb66…). dev-1 (peer, self-push lane) = ce-n8-queue-daemon-iac (S; amended
  brief at /var/tmp/BRIEF_dev1_n8_queue_daemon_iac_20260710.md; expect SELF-PUSHED PR#).
  Harvest on READY-FOR-HARVEST + full sha: bash /var/tmp/ce-pipeline.sh harvest dev-3|dev-4
  <branch> <sha>, then queue <branch> <class>.
- In-flight review results DIED with the face for: NONE (all open verdicts submitted; #959 was
  the last, approved pre-kill). Any PR the runner opens after the kill needs a fresh reviewer.
- Night lanes L1-L6 per the mandate; L2 (n1s2) and L3 (n11s1) are IN the pipeline/seats already.
  L4 (N-12 triage organ) + L5 (S-1 snapshot) not yet started. L6: keep seats stocked; canary
  ledger accumulates (terra datapoints today: dev-3 premature-signal ×3, dev-4 clean ×4 + two
  VALID structural BLOCKED escalations honored).
- Hourly PR-limbo check advised (interim N-15a): any approved-unmerged PR older than ~2 gate
  passes → investigate (stale-marker/head-mismatch class first; see arc ledger for today's cases).
- HARD STOPS (full list in mandate): no arming, no N-14 cutover, no signing, no releases, no
  credential acts, no authority widening, no relitigating, no model-adoption decisions.
- Post-drain (morning, Operator): gate redeploy (drop-in edit first), release-op ce-469,
  canary readout, PV #524, materializer arming decision, STRANGELOOP-3 draft.

## Timestamps (appended by dead-man + standby)
drill_armed: 2026-07-10T16:37:54Z (face pid 55937, session dbe6fa03, NIGHT-3 mandate fire condition met: 947+950+957 merged)
face_killed_by: self (SIGTERM to own claude PID)

## Standby section (APPEND ONLY below this line — your first acts, lane by lane, timestamped)
face_down_detected: 2026-07-10T16:37:59Z (pid 55937 gone)
standby_go_sent: 2026-07-10T16:38:59Z
standby_engaged: 2026-07-10T16:39:00Z
standby_checkpoint_read: 2026-07-10T16:39:31Z — newest durable checkpoint identified as
  RESUME_STATE_CE_DEV2_STRANGELOOP2E_20260710.md; drill protocol read end-to-end.
standby_mandate_read: 2026-07-10T16:40:15Z — ratified NIGHT-3 mandate and all eight hard stops
  read before acting; current AGENTS.md hard stops also re-read.
standby_reconcile: 2026-07-10T16:40:42Z — zero replay: #959 remained OPEN/APPROVED with a
  merge-group Validate in progress; detached runner PID 1238044 survived in
  /var/tmp/wt-ce-n15b-composition-probe and continued its original validate; durable queue intact
  with ce-529 first after n15b; dev4 remained actively building n11s1; dev1 N-8 staged work and
  focused evidence remained intact behind the host-global suite slot.
standby_lane_action_1: 2026-07-10T16:41:31Z — preserved the surviving n15b runner and queue
  instead of restarting/revalidating completed work; armed monitoring for its first post-kill PR.
standby_lane_action_2: 2026-07-10T16:41:31Z — dev3 ce-453b start gate audited rather than
  overridden. PR #956 is MERGED and its intended content is present on main, but the brief pinned
  the pre-merge head SHA 3739b552... as an ancestor (false after merge transformation). Territory
  audit also found already-delivered f1s2 overlaps signed_artifact_pins.py, so ce-453b remains
  serialized rather than starting a guaranteed-conflict duplicate lane.
standby_monitors_rearmed: 2026-07-10T16:42:07Z — face-local runner/queue/PR/fleet/disk monitor
  started in tmux session ce-codex-drill-monitor, log /var/tmp/ce-codex-drill-monitor.log.
  Existing queue-daemon, fleet-watcher, and dev-check cron were verified active/enabled and were
  not modified.
standby_authority_note: 2026-07-10T16:42:07Z — no ratification, credential, spend, arming,
  signing, release, tenant-send, model-adoption, or authority-widening act taken. Current
  repository AGENTS.md says all agents NEVER approve or merge; standby will submit only
  COMMENT/REQUEST_CHANGES review evidence and will not personally approve/merge despite the
  broader fleet-mode grant. Previously approved #959 remains eligible for the existing daemon.
standby_lane_result_959: 2026-07-10T16:44:50Z — PR #959 merged through its pre-kill review,
  approval capability, merge-group validation, and existing queue daemon. Standby did not repeat
  review, approval, enqueue, or merge; claim-closeout and dependency-unlock checks passed.
standby_lane_result_n15b: 2026-07-10T16:43:06Z — surviving runner completed n15b with exit 1 and
  correctly opened no PR. Substantive baseline-diff and governance gates were green; carrier gate
  found the one-line placeholder lacked a fenced path manifest. Pairing audit additionally found
  the branch was based before #958, so its base-to-head view reversed already-landed materializer
  paths. Governed repair dispatched in the same four-path territory to force-refresh current main,
  rebase the one four-path commit, regenerate carriers via API, and requeue for full parity.
standby_lane_result_n15b_repair: 2026-07-10T16:47:03Z — governed implementer returned
  READY-FOR-REQUEUE at 7f74d464df61e2ccef73b81fa2e0856e735bb418, conflict-free on
  post-#959 main 1360dec4c0d638de7040fedaefa4a32756cd4802. Diff is exactly four authorized
  additions; implementation/test blobs are unchanged; generated carrier declares four paths;
  focused composition tests 5 passed plus confidentiality/carrier/diff checks. n15b was restored
  to queue head behind the already-running ce-529 validator; full runner parity remains required
  before push.
standby_lane_result_dev3: 2026-07-10T16:47:03Z — ce-453b brief amended in place and re-hashed.
  Original #956 head-SHA ancestry gate was replaced by an explicit stop: #956 content landed, but
  delivered/queued f1s2 overlaps signed_artifact_pins.py. Dev3 was instructed to stop polling,
  make no edits, and emit BLOCKED-ON-PRECURSOR until f1s2 lands.
standby_lane_result_dev3_sync: 2026-07-10T16:52:06Z — provenance check caught that dev3's
  container-private brief copy still hashed 99b6e3f... and lacked the amendment, so its first
  response repeated the obsolete SHA blocker. Controller copied the amended brief into the seat,
  verified the in-seat hash exactly ed3125ff92b26034d605f4341160e27a6a11ad4948f1bcc8696b8cb452c0768c,
  and reissued only the stop amendment. At 2026-07-10T16:55Z dev3 emitted the exact required
  BLOCKED-ON-PRECURSOR signal naming ce-f1s2-preflight-env-propagation. No source edit or
  implementation start occurred.
standby_lane_result_n11s1_harvest: 2026-07-10T16:52:06Z — dev4 READY-FOR-HARVEST provenance
  verified at 41cc7e39df43cf74c18c4ae8c3e3d7b66394f580 in its dedicated remote worktree; no
  existing PR, remote branch, local worktree, or queue duplicate existed. Governed harvest
  verified the exact SHA, rebased its single five-path commit cleanly onto current main as
  9d1c7e5cec5d3da701c00520d3e4fd0340db2fc2, audited the self-inclusive generated carrier,
  and appended class M to the durable queue. Full runner parity remains required before push.
