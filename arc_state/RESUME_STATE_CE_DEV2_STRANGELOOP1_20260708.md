# RESUME STATE — CE-DEV-2 — 2026-07-08 ~19:0x — STRANGELOOP-1 ARC START (post-account-switch resume)

> Supersedes DAYARC2H. READ ORDER: MEMORY.md → DECISIONS_20260708.md (**15 items — 14+15 are the arc
> mandate**) → ARC_STRANGELOOP1_MANDATE_DRAFT_20260708.md (RATIFIED verbatim) → SESSION_RECORD_CE_DEV2_
> 20260708_EVENING.md (the discussions) → ARC_STRANGELOOP1_LEDGER_20260708.md → this.
> CONTEXT: Operator switched controller account x5→x20 and is AWAY ~9h. You are driving ARC
> STRANGELOOP-1 AUTONOMOUSLY per the ratified mandate. Ship = ARC_STRANGELOOP1_REPORT_20260709.md.

## IMMEDIATELY ON RESUME (in order)
1. RE-ARM WATCHERS (all died at logout):
   a. #907 merge watch: poll `gh pr view 907 --json state` (overwatch auth) + gate health
      (`systemctl is-active ce-queue-daemon` + failed_count grep on `docker logs ce-queue-daemon`).
   b. dev-4 signal watch: poll `sudo docker exec -e HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock
      ce-dgx-codex herdr pane read w1:p1 --source recent --lines 40` for 'READY ce-|BLOCKED ce-'
      (dedup) + quiet-18min detection.
   c. dev-3 signal watch: same via `ssh dev1 'sudo docker exec … ce-vps-codex herdr pane read w1:p1 …'`.
   d. HEARTBEAT: 25-min board re-assessment loop (restock check, stall check, watcher health).
2. VERIFY dev-3 landing (dispatch went out ~18:5x; landing verification may have died with the switch):
   pane read must show Working on the batch; if the dispatch text sits unsent in the composer, re-send
   Enter; if absent entirely, re-send pointer (brief already in-container at
   /var/tmp/BRIEF_dev3_batch_docs_preflight_20260708.md, sha 3b2d0409…59f10a7).
3. CHECK #907: if MERGED → DISPATCH dev-1 hermes R2 immediately (the one serialized unit):
   brief /home/cedev2/creator-engine/.ce/briefs/BRIEF_dev1_hermes_retirement_R2_20260708.md
   (SELF-PUSH NON-DRAFT framing, controller-corrected; sha256sum it fresh at dispatch). dev-1 access:
   `ssh dev1 'tmux send-keys -t ce-dev1-orchestrator:2.0 …'` per pointer+SHA protocol (non-contained
   seat, reads repo files directly — pointer to the brief path + sha suffices).
   If #907 CI failed AGAIN: investigate on FRESH origin/main only (stale-baseline lesson ×3 today).
4. Then run THE LOOP per mandate: on READY/PR → fresh reviewer (worktree FETCHED FRESH first) →
   mechanical fixes at harvest → approve as ce-dev-2 → gate merges → RESTOCK freed seat from pool.

## IN-FLIGHT SET (P0)
- dev-4 Working: ce-conveyor-intake-s1 (story) + ce-491-prearming (task). COMMIT-ONLY → harvest_intake
  on READY (recipe = #904/#907 harvests). Claims: .ce/claims/ce-conveyor-intake-s1.md + ce-491-prearming.md.
- dev-3 Working (verify per §2): 3 units, SELF-PUSH non-draft. Claim: .ce/claims/ce-dev3-batch-docs-preflight.md.
  KNOWN OVERLAP: test_pr_preflight.py also appended by dev-4 unit B — dev-3 brief mandates rebase-check
  vs origin/ce-491-prearming before push.
- dev-1 idle, parked WIP 01bb16fa: hermes R2 dispatch gated ONLY on #907 merge (brain-ledger tail).
- PR #907: head 5264891ea (revert of bad harvest-fix), APPROVED by ce-dev-2, CI rerunning at checkpoint.
  Original dev-4 links are CORRECT on post-#906 main.

## RATIFIED POOL (pull next as seats free — order + full specs in the mandate file)
P1 #512 redeploy portability → P2 Acceptance-Evidence bot rule → P3 #509 rehearsal harness s1 →
P4 #513 design artifact (morning review) → P5 #511 seat-watch daemon s1 → P6 dev-4 egress-broker
deploy + self-push canary (CONTROLLER host op) → P7 Ring-1 live smoke (controller op, decision 4b) →
P8 review-daemon s1 dry-run → P9 closed-but-not-real research sweep.
OUT (never autonomous): Arad send (waits on rehearsal per Decision 15) · Nitzan D6 · materializer
arming · automerge widening · release/signing ceremony · outward-facing anything.

## RAILS (Decision 14, short form)
Fresh-context review + FULL CI-parity preflight before every approve; author≠reviewer; brain-ledger
units strictly serialized (hermes R2 holds the tail next); /compact free; canonical `ce launch` relaunch
pre-authorized on crash or >45% ctx; gate outage → redeploy via
`bash deploy/singleton-redeploy/redeploy-singleton.sh --daemon queue-daemon --repo-root /home/cedev2/ce-daemon-main`
(memory: ce-queue-daemon-systemd-dgx-deployment); gap → ops_triage ticket, promote only if pool-blocking;
checkpoint after every material event; append EVERY event to ARC_STRANGELOOP1_LEDGER_20260708.md.

## AUTONOMY MECHANISMS (installed 2026-07-08 ~19:5x per Operator sign-out directive)
- IN-SESSION: 4 event watchers (907-trigger, dev-4, dev-3, heartbeat) + session cron "13,48 * * * *"
  = full dev check (work state, ctx%, limit errors, restock decision, ledger append).
- HEARTBEAT LIVENESS FILE: /home/cedev2/.ce/strangeloop1-heartbeat (epoch, touched every 25 min).
- HOST WATCHDOG (survives controller death): crontab `*/10 * * * * /home/cedev2/.ce/
  strangeloop1-watchdog.sh` → telemetry to .ce/state/research/STRANGELOOP1_WATCHDOG_LOG.txt
  (gate, seat panes+ctx%, controller-heartbeat age; flags STALE >45 min). TELEMETRY-ONLY by design
  (one-face singleton: never spawns a second controller). A RESUMED controller must read its tail
  to reconstruct any dead-controller gap, then REMOVE the crontab line when the arc ends.
- SEAT LIMIT CONTINGENCY (Operator, sign-out): seats ride the x20 GPT Plus account; on session/
  weekly limit errors, SWITCH SEATS to the second OpenAI account per playbook memories
  ce-openai-account-switch-playbook + ce-account-switch-scope-discipline (account B staged at
  dev1 ~/.codex-acctB; JWT-decode auth.json to identify; validate staged auth in THROWAWAY
  CODEX_HOME only; relaunch = canonical ce launch only).

## ⏸️ AWAITING-OPERATOR (morning queue — full paths)
1. T5.1 preview: /home/cedev2/creator-engine/tmp/ce-welcome-pack-t5/index.html
2. Arc report: /home/cedev2/creator-engine/.ce/state/research/ARC_STRANGELOOP1_REPORT_20260709.md (Ship)
3. #513 design artifact (P4 output — path lands in ledger when produced)
4. Nitzan D6 · Arad send (post-rehearsal, Decision 15)
