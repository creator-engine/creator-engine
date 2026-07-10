# RESUME STATE — CE-DEV-2 Controller — CONVEYOR MODE — 2026-06-25T23:35Z

## SEAT IDENTITY & TOPOLOGY
CE-DEV-2 controller on DGX (spark-b824, uid1003). Contained codex seats (gpt-5.5/high): dev-4=`ce-dgx-codex` (DGX local), dev-3=`ce-vps-codex` (VPS via `ssh dev1 'sudo docker exec …'`), dev-1=codex tmux `ce-dev1-orchestrator` (VPS). Drive via herdr `pane read/agent send w1:p1` + `pane send-keys w1:p1 Enter`. gVisor → only bind-mounts host-visible. Author=ce-overwatch (`~/.ce-keys/overwatch.env`), reviewer=ce-dev-2 (`~/.ce-keys/ce-dev-2.pat`). ISSUES=ce-ops, CODE=creator-engine.

## OPERATING MODE: CONVEYOR (Operator sign-out 2026-06-25) — [[ce-controller-conveyor-intake-directive]]
Hourly ScheduleWakeup loop (next 00:20Z): check #249 ruling→exec MOVE / verify board / tend+re-stock / extract. Crons: seat-check :00, poll-devs :05, belt-canary :03/5m, conveyor-tend :30.

## ✅ DELIVERED (conveyor) — 9 PRs merged
ce252(#480) ce250(#481) ce240(#482) ce253(#483) ce25(#484) ce226(#485) ce190(#486) ce177(#488, was #487-collision). All host-validated, governed, armed-wall-merged. Board CLEAN, 0 open.

## ⏸️ AWAITING-OPERATOR (surface FIRST on return)
**ce-ops#249 MOVE-PR scope ruling** (comment 4804990125). Recon (tmp/move-pr-plan.md): move-TO already done (19 files in ce-ops); it's delete+de-link only. De-link cascade lands in sibling internal docs (docs/delivery cluster=half-gutted) + broader docs/devops/openbao/** surface. Ruling: A narrow / **B whole-tree (rec)** / C +openbao. HOLDING until ruled (narrow exec would waste de-link work). NOTE: docs/keys/ce-root-v1 verified NOT a leak (public OpenSSH allowed_signers trust anchor) — do NOT delete.

## SEATS @23:35Z — IDLE, QUOTA-LIMITED (4 passes)
All delivered full queues; dev-1 stuck "5h 10% left", dev-4/dev-3 idle. RE-STOCK SKIPPED 4 passes (need >20%; rolling window should refill while idle — get FRESH readings next pass). Rate-limit DIALOG → answer "2" (keep gpt-5.5, never mini).

## NEXT-DISPATCH SLATE (when quota recovers)
#107 (§7 forge-op guard), #222-residual, #240-C3 parity-harness, #166-slices. AVOID: #242/#243 (stub), #224 (dev-1 owned), #239/#234 (Operator-gated W5), epics #166/#217.

## LESSONS THIS SESSION (in loop prompts)
- main-drift → rebase onto origin/main (the #481 cause).
- carrier branch-slug collision → RENAME THE BRANCH (#487→#488); run `verify-path-manifest --require-carrier` LOCALLY (pytest doesn't cover it). [[ce-carrier-verify-require-carrier-gap]]
- seats have no pytest → their "done" can be red; ALWAYS host-validate before push.
- verify "key material" flags before alarming/deleting (docs/keys/ce-root-v1 = intended-public).

## RESUME RULE
Newest `RESUME_STATE_CE_DEV2_*` by mtime + MEMORY.md first. NEVER `.hermes`. Dual-write CE-DEV-1. Loop self-re-arms hourly; ~/ce-conveyor-pass.log = running record.
