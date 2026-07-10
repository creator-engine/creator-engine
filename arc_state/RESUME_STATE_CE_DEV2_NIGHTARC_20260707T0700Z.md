# RESUME STATE — CE-DEV-2 — 2026-07-07 ~07:00Z — NIGHT-ARC morning checkpoint (pre-/clear)

> READ ORDER: MEMORY.md → .ce/state/decisions/DECISIONS_20260707.md (+ 20260706) →
> this file → NIGHTARC_MANDATE_CE_DEV2_20260706_NIGHT.md (the live arc SSOT, D1-D8 ratified).
> RULES: NEVER pass `model` on pinned-role Agent spawns; reviewer baseline via `git show
> <merge-base>:` only / staged .review-artifacts. Herdr: Enter as SEPARATE send-keys; if seat
> mid-turn Enter→Tab (queues). Verdict evidence to a FILE in-container. Account-switch scope:
> validate staged auth in THROWAWAY CODEX_HOME only — controller auth OUT OF SCOPE.

## LIVE ARC = NIGHT (ratified D1-D8 all yes). Two north stars: (A) containerized controller at
## parity, (B) whole fleet same signed version. Hard stops: NO external comms/sends (Arad/Nitzan/
## public), NO signing, NO dep-unlock arming, NO mythos/settings changes, NO dev-1 containment
## EXECUTION, gate never leaves CE-DEV-2.

## SHIPPED (day+night): 7 merges — #869 #866 #865 #871 #867 #873 #870.
P0 CHAIN COMPLETE ON MAIN: #866 posture banner + #871 takeover core + #873 refusal-that-teaches.
First P2 on main: #870 signing-deputy design. #867 drift gate live. Main head 19a7f44e (#870).

## BOARD (9 open, all mid-cycle)
- #859 APPROVED but STUCK IN A LOOP: daemon skips it `approval_capability_reason=expired` — my
  re-approval's capability marker expires before the daemon's pass acts. STRUCTURAL, not retry.
  FIRST ACTION: diagnose (marker TTL vs daemon interval; wall-daemon token vs approval-capability
  marker lifetime). Likely needs the marker minted with longer TTL or daemon to re-check.
- #864 CHANGES_REQUESTED DIRTY — R3 delta re-review owed (dev-3 was to verdict); rebase needed.
- #868 CHANGES_REQUESTED — R2 at dev-3 (4 findings: packaging/state-machine/idempotence/tests).
- #872 CHANGES_REQUESTED — R2 at dev-3 (TOCTOU flock fix).
- #874 CHANGES_REQUESTED, R2 PUSHED head 2575b6a0 (drill: run_at+host_id, abort JSON record) —
  DELTA RE-REVIEW IN FLIGHT (agent a4552128ecc3dfdd8, worktree .ce/wt-874r2-review). On APPROVE:
  gate → then DRILL #1 (D6) executes.
- #875 CHANGES_REQUESTED, R2 READY head b746ee01 — HARVEST IN FLIGHT (agent a339bd27ccf7dcc54).
  Blocking was lazy-TTL; R2 must add an ACTIVE revocation sweep.
- #876 (486 next-step hints), #877 (485 journey doc pair), #878 (487 shape --from) — all
  REVIEW_REQUIRED, dev-1-authored, NEED independent review (journey program N-C; review bars =
  the ratified vocab rulings: no bet/appetite, Goal/Done-when/Change-type, Budget opt-in %, CLI-
  anchored, honest loop, packs LINK; #877 MUST teach `ce brain init` + `ce launch --backend host`).

## SEATS (all at stop points; multi-unit standing policy)
- dev-1 (tmux, neckar acct verified 61%): journey PRs #876/#877/#878 all READY+pushed; #874 R2
  pushed; #408 containment prep BLOCKED (correctly — #872 read-lane not merged; no dry-run
  fabricated). IDLE — restock after reviews: P2 designs #482/#483/#484, or 874 R3 if needed.
- dev-3 (ce-vps-codex, neckar verified 61%, BROKER SELF-PUSH per D7): #875 R2 READY b746ee01
  (harvest in flight); prior: #868 R2, #872 R2, #489 (U7) status UNKNOWN — VERIFY what landed.
  #461 still gated (adoption template lacks merge_group). ctx ~81% (freshly relaunched).
- dev-4 (ce-dgx-codex): ce-490 DRAINED-FOR-SWITCH at 84960c24 (BLOCKED-ENV, needs harvest);
  #479/#480 batch5 status UNKNOWN — VERIFY. SESSION_ID 019f308e-0c44-79b1-b757-e95516e26c8f.
  ⚠️ STILL ON amitaicoco1 (<10%) — codex rate-limit dialog was blocking its pane (dismissed
  option 3). NEEDS THE ACCOUNT SWITCH: drain done → swap host auth /home/cedev4/.codex/auth.json
  to neckar (already staged there? VERIFY via JWT-decode) → canonical relaunch (runsc script,
  NOT raw codex) → codex resume 019f308e → /status confirm neckar. ctx ~32%.

## CONTROLLER OPS (night set-pieces — NONE executed yet, all blocked on merge-lane/switch)
- C5 CUTOVER (D1): PRE-FLIGHT GREEN + banked (ce-daemon-main@fd548615 has #853; BAO token live
  30d; env has CE_DAEMON_IMAGE+REPO_ROOT; manual smoke GREEN /var/tmp/c5-manual-pass{1,2}.log).
  BLOCKED on zero-in-flight window which #859's loop prevents. Cutover cmd = staging doc
  A2_QUEUE_DAEMON_CUTOVER_STAGING_20260704.md lines 83-98. ROLLBACK: docker stop ce-queue-daemon;
  bash ~/ce-wall-daemon-launch.sh. Daemon pid 200363 healthy (stdout → session scratchpad
  rollback-relaunch.log). Smoke bug ticketed ce-ops#492.
- SHADOW CANARY (D3): not started (behind C5).
- DRILL #1 (D6): blocked on #874 merge.
- dep-unlock shadow audit (N-D): not yet read tonight.
- Tickets filed night: ce-ops#489 #490 #491 #492 (+ day #485-#488).

## RE-ARM on resume
1. Kill stale watchers (pgrep -f scratchpad), re-arm board + seat (scripts in scratchpad;
   /tmp/seat_watch_handled has processed-signal filter). Dedup on echoes.
2. Two agents in flight: harvest #875 R2 (a339bd27ccf7dcc54), review #874 R2 (a4552128ecc3dfdd8)
   — collect via SendMessage or task-notification; act on verdicts.
3. Verify seat build outcomes that are UNKNOWN: dev-3 #868/#872/#489, dev-4 #479/#480/#490.
4. Complete dev-4 account switch (see SEATS above).
5. Then unblock #859 → C5 window → cutover → shadow canary.

## ⏸️ AWAITING-OPERATOR (surface FIRST, unchanged)
1. Arad send (readiness note today; T4 pack rewrite = Operator's codex session).
2. Nitzan D6 answers (most overdue).
3. #474 tenant half (mythos protection floor).
4. 0.3.4 cut + co-sign ceremony (assembly ready today; signing = Operator co-sign).
5. Promotion-cell flip + dep-unlock arming — not evidence-ready yet.

## ⏫ DELTA ~07:1xZ (pre-clear)
#874 R2 APPROVED + QUEUED (VERDICT-874R2 both blockers closed: run_at+host_id, distinguishable
abort JSON). Slice D done → the ENTIRE ratified #471 P0 program is now implemented (banner+core+
refusal+drill). ON #874 MERGE: execute DRILL #1 (D6) — benign gate cycle via codex standby,
evidence-packeted. #875 R2 harvest (a339bd27ccf7dcc54) still in flight. Reviewer venue via
in-process agent + SendMessage re-staging worked (874 R2 was blocked on staging, redirected).

## ⏫ DELTA ~04:0xZ (post-/clear session, Operator present: "drive the arc, devs at stop lines")
MERGE-LANE ROOT CAUSES DIAGNOSED (both "structural loop" PRs — NOT marker-only):
- The daemon DID enqueue; GitHub merge queue dequeues on merge_group `Validate` FAILURE (~7-8min
  round trip), then the approval-capability marker (TTL 600s) is expired on the next pass →
  permanent skip loop. Marker gap ticketed via ops_triage.
- #859 merge_group failure: its new test yaml-parses CE_WORKFLOW_CONTENT and exposes a LATENT
  MAIN BUG — _render_ce_workflow_content() is a non-raw f-string, so template's
  rb"\1<published-with-this-spec>" compiles \1 → chr(1). TENANT-FACING: rendered adoption
  workflows canonicalize ≠ signer (release_publish.py uses correct r"\1") → content_sha256
  mismatch → tenant spec-verify FAILS CLOSED. Fix routed INTO #859 (rebase+escape+regression).
- #874 merge_group failure: .ce/brain/assertions.yaml append chain forks after merge (its
  prev_hash e314d69e vs main tail 2222984b seq145) → ledger invalid → doctrine-coverage fails in
  EVERY example check → 37-test sweep failure. Fix: rebase + re-chain via canonical tool.
- #875 R2 harvest agent: preflight FAIL (correctly not pushed) — R2's new peercred test socket
  filename → AF_UNIX 108-byte limit under xdist gw10+. One-line R3 fix dispatched to dev-3.
DISPATCHED: dev-1 BRIEF_dev1_morning_20260707 (U1=#859 rebase+\x01 fix, U2=#874 rebase+rechain;
U2 first) — Working confirmed. dev-3 BRIEF_dev3_875r3 — Working confirmed.
AGENTS IN FLIGHT: 3 reviewers (#876/#877/#878, staged wt-<n>-review, mb=19a7f44e), 1 utility
(dev-4: pre-stop bundle extraction → auth verify → canonical relaunch → resume 019f308e →
/status verify neckar), 3 ops_triage (marker-expiry gap; tenant canonicalization remediation;
account-switch codification re-ticket).
WATCHERS: board-watch.sh + seat-watch.sh re-armed (this session's scratchpad).
NEXT ON FIRE: dev-1 pushes → delta re-reviews → re-approve #859/#874 (re-approve RIGHT WHEN
merge_group can pass; marker fresh) → merge → DRILL #1 (D6) on #874 merge → zero-in-flight →
C5 cutover → shadow canary. dev-4 report → restock its queue.
TICKETS LANDED (~04:1xZ): ce-ops#493 (marker-expiry wedge), ce-ops#494 (tenant canonicalization
remediation — CONFIRMS broken escape since 2026-06-19 8cc07222 → Mythos/Arad repo onboarded
07-03 IS AFFECTED; fold into Arad-send readiness note), ce-ops#245 updated (account-switch SSOT
lives in ce-ops — memory corrected, it DID land via PR#454→relocated by #494 split).
DELTA ~04:4xZ: dev-4 SWITCH COMPLETE+VERIFIED (neckar, 58% weekly, session 019f308e resumed;
5 pre-stop bundles in /home/cedev2/ce-harvest-staging/dev4-preswitch-20260707/ incl ce-490
84960c24, ce-479 a3b62990, ce-480 b8d6d6b0 — batch5 status query sent to dev-4, awaiting).
JOURNEY REVIEWS ALL POSTED — #876 RC (unconditional scope_next hint + JSON next; controller-id
default change), #877 RC (quickstart steps 3+5 not paste-able: ce shape needs slug, ce ratify
needs --approver-ref), #878 RC (no size guard on PRD read_text). Combined R2 brief staged:
/var/tmp/BRIEF_dev1_journey_r2_20260707.md on dev1 — DISPATCH ONLY when dev-1 signals on
U1/U2. #875 R3 harvest agent in flight. Fleet ALL on neckar.
DELTA ~05:2xZ: #864 APPROVED on dev-3's R3 verdict but CONFLICTING — its ledger delta is a
MID-CHAIN RE-PIN cascade (d1b-13 evidence_sha256 → downstream prev_hash cascade) computed on a
stale ledger. INTEGRATOR PLAN (mine, ce-overwatch-authored PR): rebase AFTER #874 merges (both
rewrite the ledger tail; 874 first), take main's assertions.yaml, re-run the d1b-13 re-pin per
94e4a32b's mechanics, push, delta-check, re-approve. Pattern feeds ce-ops#491 (serialization).
#875: R3 code GREEN but carrier stale (R2 test file missing, class story→feature floor) — R4
mechanical carrier fix queued at dev-3 with exact values (new sha 2db1b96f...). #868 R2 harvest
in flight (carrier pre-check first). #874 auto-re-enqueued by GitHub (auto-merge armed) — will
fail merge_group again until dev-1's rechain push; expected noise, ignore.
DELTA ~05:5xZ: dev-4 batch5 BOTH READY (ce-479 a3b62990, ce-480 b8d6d6b0 — commits were already
complete, evidence regenerated post-restore). HARVEST QUEUE (throttle: max 2 concurrent
preflights): #872 R2 (running), #489 (running), then #479, then #480. #875 R4 89c7f040 →
resumed original harvest agent. #868 R2 delta re-review in flight. dev-1: U1+U2 both in flight
with subagents.
