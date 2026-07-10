# RESUME STATE — CE-DEV-2 Controller — CONVEYOR MODE — 2026-06-25T18:51Z

## SEAT IDENTITY & TOPOLOGY (read first)
- **I am CE-DEV-2**, controller on the DGX Spark (`spark-b824`/100.100.105.50, GB10 aarch64, user `cedev2` uid1003). Permanent controller, RAW HOST PROCESS (the #240 authority-leak — being contained via dispatched #240).
- Fleet contained codex seats (gpt-5.5/high): **dev-4**=`ce-dgx-codex` (DGX local), **dev-3**=`ce-vps-codex` (VPS, `ssh dev1 'sudo docker exec ce-vps-codex …'`), **dev-1**=codex in tmux `ce-dev1-orchestrator` (VPS, `ssh dev1`). Drive via herdr `pane read/agent send w1:p1` + `pane send-keys w1:p1 Enter`; **gVisor → only bind-mounts are host-visible** (route bundles via `/workspace/creator-engine/tmp/` ⇒ host `/home/<user>/...creator-engine/tmp/`; `/var/tmp` shared across execs for briefs).
- Author=ce-overwatch (`~/.ce-keys/overwatch.env`→`CE_OVERWATCH_PAT`). Reviewer=ce-dev-2 (`~/.ce-keys/ce-dev-2.pat`). ISSUES=ce-ops; CODE=creator-engine.

## ⭐ OPERATING MODE: CONVEYOR (Operator sign-out directive 2026-06-25)
Full directive in memory **[[ce-controller-conveyor-intake-directive]]**. I own ALL dev intakes (extract→validate→push→review-as-ce-dev-2→armed-wall-merge) until self-push/review go live (#242/#243). Foreman, NO inlining — drive via workers conforming to CE roles [[ce-worker-roles-and-dispatch]]. Saturate ~6 codex threads via QUEUE-stocking. /compact idle seats >40%.
- **Hourly conveyor loop ARMED** via ScheduleWakeup (next 19:51Z): tend→extract→push→review→re-stock→verify. Re-arms itself.
- **Crons:** `ce-seat-check.sh` :00, `poll-devs.sh` :05 (read-only), belt-canary pickup :03/5m, **`ce-conveyor-tend.sh` :30** (NEW — /compacts IDLE seats >40% via herdr; logs `~/ce-conveyor-tend.log`).

## SEATS — DISPATCHED 18:50Z (all Working, 2-unit queues)
| Seat | PRIMARY | QUEUED | Briefs in container `/var/tmp` |
|---|---|---|---|
| dev-4 | **ce-ops#240** contained-controller C1 image (kill ambient-token anti-pattern in `deploy/dgx-controller-runsc/`, stub cred-injection seam) | ce-ops#226 cockpit operator-peek | brief-ce240.md, brief-ce226.md |
| dev-3 | **ce-ops#253** controller awaiting-decision inbox (extend `forge/review_pickup.py`) | ce-ops#25 `ce --version` (extend `_version.py`) | brief-ce253.md, brief-ce25.md |
| dev-1 | **ce-ops#190** `ce update` signed in-place | ce-ops#177 brain drift-CI (extend `ce_brain_drift.py`) | /var/tmp/brief-ce190.md, brief-ce177.md (VPS host) |
Each brief: implementer role, embedded ticket, branch slug, carriers+work-class+FULL-suite-from-repo-root DoD, stop-line (commit→suite→report SHA, NO push). Seats report SHA+branch → I extract.

## OPEN PRs @18:51Z (approved, awaiting CI → armed wall merges)
- **#480** feat(ce-ops#252) ship `ce validate-pr` — ce-dev-2 APPROVED. (I fixed dev-4's uncaught validate-pr docs failure; manifest 10 paths ae03da7c.)
- **#481** fix(ce-ops#250) clear stale herdr session on relaunch — ce-dev-2 APPROVED.
Today merged autonomously through armed wall: #444/#445/#479 (+ ~37 day-shift).

## NEXT-DISPATCH SLATE (merge-log-vetted, after current queues)
Ready: #107 (§7 forge-op guard), #222-residual (verify thin first). AVOID: #242/#243 (**DISPUTED done** — broker is stub skeleton, seats empirically can't self-push; keep OPEN), #224 (in-compose dev-1), #239/#234 (Operator-gated W5/security), #166/#217 (epics — dispatch slices). Done-close-sweep candidates (verify each): #245/#188/#252/#233/#238/#235/#65.

## NEXT ACTIONS ON RESUME
1. Run the CONVEYOR PASS (the ScheduleWakeup prompt has the full procedure). 2. Extract any seat that reported SHA+branch. 3. Re-stock empty queues. 4. Confidentiality MOVE PR (ce-ops#249, task #3 — still pending, lower priority). 5. Surface Operator-decisions with ⏸️ AWAITING-OPERATOR.

## RESUME RULE
Newest `RESUME_STATE_CE_DEV2_*` by mtime in `.ce/state/research/` (DGX) + MEMORY.md first. NEVER `.hermes`. Dual-write CE-DEV-1.
