# RESUME STATE — CE-DEV-2 Controller · 2026-06-21 · MERGE-QUEUE LIVE + BRAIN 7-SLICE LADDER + DEV-4 RESTORED

**WRITTEN BY / WHERE:** CE-DEV-2 controller as `cedev2` on the **DGX `spark-b824`** (tailnet `dgx-spark-1`/100.100.105.50, GB10, aarch64), cwd `/home/cedev2/creator-engine` (now on branch `main`), Opus 4.8 effort-high. **SUPERSEDES** `RESUME_STATE_CE_DEV2_20260621_EOD_ARAD-BELT-QUEUE-BRIDGE.md`. Read this + `MEMORY.md` first. **main = `70413787`** (#302 belt).

## PEER-SEAT → HOST → REACH (verified 2026-06-21)
- **THIS host = DGX.** dev-2 laptop = separate peer, not this session.
- **dev-1** = codex user `ce-dev-1` on VPS → `ssh dev1`, tmux pane **%0** (`ce-dev1-orchestrator`). Self-pushes.
- **dev-3** = codex user `ce-dev-3` on VPS → `ssh dev3`, tmux pane **%2** (`dev3-onboard`). Self-pushes.
- **dev-4** = CONTAINED codex on DGX → `ssh cedev4@localhost -i ~/.ssh/id_ed25519`, tmux pane **%0** (`dev4stage1`). checkout `~/ce-workspaces/creator-engine`. **NOW PUSH-CAPABLE AGAIN** (see below). ⚠️ NEVER raw-relaunch via `codex` — [[ce-seat-relaunch-canonical-launch-only]]. /compact for context, not C-c.
- gh as overwatch: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT` (ce-overwatch, admin; has **projects + org** scope now).
- WAKE recipe: write brief→file, `scp` to host, `ssh <host> 'tmux send-keys -t <pane> C-u; send-keys -t <pane> -l "$(cat /tmp/x)"; send-keys Enter; sleep 1; send-keys Enter'`. (Quoting: use the file+cat method — apostrophes/parens break inline.)

## 🟢 NEW TOOL: fleet dashboard — `bash ~/fleet-status.sh`
One-glance seats (working/idle + branch + context%) + open PRs (review/mergeable/CI) + program-board roll-up. Use it every tick instead of pane-peeking. "idle ≠ done" — verify completion via PR state + `gh pr view <n> --json commits` (last-commit author/time), not the footer.

## ⏰ RE-ARM ON RESUME (session-only crons — DIE on /clear)
1. **`0408e97f`** — Team-upgrade checkpoint, fires **22 Jun 16:57 UTC**. If resuming before then RE-CREATE: CronCreate `57 16 22 6 *`, recurring:false → probe `gh api repos/chmod735-dor/mythos/rulesets`; 200→apply CE protection floor on mythos; 403→PushNotification Operator it's due.
2. **`c651cd45`** — watch+route loop (every :17/:47). RE-CREATE on resume (prompt in prior turns: dashboard + route freed foremen to next brain slice + watch #300 enqueue).

## ✅ MERGE QUEUE IS LIVE (the session's structural win)
Ruleset **`ce-reference-protection-floor` (id 17946690, active)** on `main`: rules = `required_status_checks`(strict, "Validate governance artifacts") + `pull_request`(1 approval, **dismiss-stale ON, last-push ON**) + `merge_queue`(SQUASH, ALLGREEN, 5/5/1/5min/60min). Classic branch protection still active underneath (keeps `enforce_admins` + code-owner). **The surgical bridge is retired.** Authors NO LONGER rebase-and-wait — the queue rebases server-side; approval survives `merge_group`. To merge: `gh pr merge <n> --squash` = **enqueue**. Runbook: `docs/operations/MERGE_QUEUE_ENABLEMENT_RUNBOOK.md`. ⚠️ §4 approval-survival acceptance test NOT yet formally run on throwaway PRs — #300 is the first real-PR test (watch it).

## MERGED THIS SESSION: #301 (merge-queue) · #302 (belt) · #300 (mint-broker) ENQUEUED (queue pos 1, merging).
## main = 70413787.

## OPEN PRs (use the queue — `gh pr merge <n> --squash` enqueues)
- **#300** ce157 mint-broker (ARAD P0) — **ENQUEUED, position 1** (head cc1f919b, APPROVED). Should merge hands-free. After merge: S7–S10 fast-follows + signed 0.2.0 republish.
- **#304** ce176-brain-probe (= brain F2/#176) — dev-3 addressing dev-1's CHANGES_REQUESTED.
- **#299** ce-fwheel1 (wheel-gate relax, #257-style merge grant) — CHANGES_REQUESTED + conflicting; the wheel-conflict killer; needs author fix + re-review.
- **#294** ce158 trust-anchor (dev-1) — CHANGES_REQUESTED + conflicting.
- **#303** ce23 baseline attestation (dev-3) — REVIEW_REQUIRED + conflicting.

## COMPANY BRAIN PILLAR — epic #79, 7-slice ladder (native sub-issues, 1/7 done)
Two layers behind one MCP surface, SSOT-first. **F6 RATIFIED 2026-06-21 (Option A):** vector store=**sqlite-vec**; embeddings=**EmbeddingGemma-300m local-first, GPU-auto on DGX, heavy INGEST routed to DGX GPU**; privacy=**local-only for ce-ops, API opt-in per-scope consent** (`requires_egress×scope` fail-closed). Full design: `~/F6_recall_design.md`.
- F1 #167 ✅ merged (#298, ledger). 
- **F2 #176 → PR #304** (in review). · **F3 #177** (blocked on F2 merge). · **F4 #178** (dev-4 building — load-bearing bootstrap). 
- **F6.1 #179 · F6.2 #180 · F6.3 #181** (recall MVP, queued). 
- Highest-leverage = F4 (makes the brain consulted at bootstrap, reuses #163 injection). Recall (#179-181) builds in a freed-foreman cycle.

## SEATS (as of checkpoint; verify via dashboard)
- **dev-1** WORKING ~14% ctx (low → will /compact) — re-approved #300, then F4(#178)? It SAW #178 may be locked by dev-4; reconcile via the 🔒 claim.
- **dev-3** idle ~35% — was fixing #304; re-route to push the #304 fix / re-request dev-1.
- **dev-4** RESTORED, routed to **F4 #178** (post `🔒 in-compose dev-4` first). Strongest machine.

## DEV-4 CREDENTIAL — FIXED + VERIFIED (#175 closed)
Root applied `chmod u+s /usr/bin/bwrap` (Ubuntu 24.04 unprivileged-userns/AppArmor blocked non-setuid bwrap). `~/.codex/config.toml` has `[shell_environment_policy] set = {GH_TOKEN, GITHUB_TOKEN}` (the ce-dev-4 PAT). Verified: in-sandbox GH_TOKEN present + `git ls-remote` authenticates. Self-pushes again; workaround retired. Durable follow-up (a) App-mint JIT helper still on #175.

## BELT (#55) — MERGED but NOT deployed; durable redesign chosen
`ce pickup poll` is in main, but `/notifications` feed **rejects fine-grained PATs (403)**; fleet uses fine-grained → **Operator ratified redesign to Search API** (`review-requested:@me` etc.). Filed **#182** (dispatch-ready). Worktrees `~/.ce-belt` staged on dev-1/dev-3. After #182 lands + a fine-grained PAT in `~/.ce-keys/<id>.pat`, deploy canary (poll+`--claim`, `--enable-launch` WITHHELD). Invocation: `python3 -m creator_engine_validator.ce_cli pickup poll ...`. Until belt is live, **controller manually routes freed foremen** (the watch loop does this).

## PROGRAM BOARD — now machine-readable + writable
Overwatch token gained **projects+org** scope (Operator granted). Board = `orgs/creator-engine/projects/1` ("CE Program Board"); epic progress bars on the issue pages (e.g. #79 = 1/7). Today's active work synced + native sub-issues wired #79→slices. Status lanes: In flight/In review/Queued/Post-pitch/Done. fleet-status.sh rolls it up.

## ⏸️ AWAITING-OPERATOR / STANDING
- **🗓️ Mon 22 Jun ~17:00 UTC — GitHub Team upgrade on `chmod735-dor`** (web-UI billing; gates mythos protection floor for Tue 23 reviewer-floor rehearsal → Wed 24 Arad). Cron 0408e97f verifies.
- Arad chain: #300 merge → S7-S10 + 0.2.0 republish → Team upgrade → mythos floor → Tue 23 rehearsal (real mythos) → Wed 24 Arad (fallback Sat 27).

## TICKETS FILED THIS SESSION
#176/#177/#178 (brain F2/F3/F4) · #179/#180/#181 (recall F6.1-3) · #182 (belt Search-API redesign). #175 CLOSED (dev-4 cred). F6 ratified on #79. Belt finding on #55.

## MEMORIES WRITTEN: [[ce-seats-foremen-self-managed-fanout]] · [[ce-seat-relaunch-canonical-launch-only]].
