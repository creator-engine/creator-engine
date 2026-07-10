# RESUME STATE — CE-DEV-2 · 2026-06-22 ~03:35 UTC · POST-WAKE: arc complete, #309-land chain in flight, 3 ops decisions pending

**WRITTEN BY/WHERE:** CE-DEV-2 controller as `cedev2` on the **DGX `spark-b824`** (tailnet dgx-spark-1/100.100.105.50, GB10, aarch64), cwd `/home/cedev2/creator-engine` on `main`, Opus 4.8 effort-high. SUPERSEDES `RESUME_STATE_CE_DEV2_20260622_NIGHT-ARC-COMPLETE.md`. **Read this + MEMORY.md first.** main ≈ `627b4217` (21 merged).

## PEER-SEAT → HOST → REACH (verified)
- THIS host = DGX. dev-1 `ssh dev1` %0 · dev-3 `ssh dev3` %2 (both VPS, ce-dev-{1,3}) · dev-4 `ssh cedev4@localhost -i ~/.ssh/id_ed25519` dev4stage1:%0 (DGX, full-auto).
- overwatch gh: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. ce-dev-2 PAT: `~/.ce-keys/ce-dev-2.pat`.
- **⚠️ VPS scp BROKEN (/tmp tmpfs 100% full).** Send VPS nudges via pipe: `cat localfile | ssh devN 'cat > ~/f.txt'` then `ssh devN "tmux send-keys -t %P C-u; sleep 1; send-keys -l \"$(cat ~/f.txt)\"; Enter; sleep 2; Enter"`. NOT scp.
- Seats: codex auto-compacts near limit (don't panic-restart); use gh CLI not MCP connector; merge queue occasionally ejects a PR un-merged → just re-enqueue (`gh pr merge <n> --squash`).

## ⏳ LIVE CHAIN (the thing to drive): floor-fix → land #309 → G6+G8 batch
1. **Floor-fix (Operator-ratified):** dev-3 (G5 author) building a PR to EXCLUDE test-file LOC from the work-sizing floor (size on SOURCE LOC only). It reports back #309's source-only count + the `feature` ceiling. → review (non-author) → merge.
2. **Land #309 (F6.3):** once floor-fix merges, #309 re-runs the gate with tests excluded (834 source vs `feature`). If clears → passes legitimately + enqueue. If not → documented pre-gate **grandfather override**. #309 is code-APPROVED (all 4 review findings fixed) + 128 brain/recall tests green; SIZE was its only blocker. Merging it → **ladder 7/7 + unblocks G9 + G11**.
3. **G6 enforce-flip + G8 belt launch-arm = BATCH, RATIFIED, gated on #309 LANDING. Execute BOTH the moment #309 merges — NO further ask.** G6 = flip seat_class in `hook_check.py` warn→ENFORCE. G8 = deploy belt poll+claim with `--enable-launch` ON (belt is canary-clean: bugs #313/#317/#321 fixed). NOTE: belt per-seat canary DEPLOY may still need standing up (the feed merged + validated, but the per-seat poll loop/timer + a fine-grained PAT in ~/.ce-keys/<id>.pat per seat).

## 3 OPS DECISIONS — walked with Operator, AWAITING THEIR CALL (re-surface post-clear)
- **(6) G5 PR-template** — a template EXISTS (`.github/pull_request_template.md`) but predates G5 → lacks the work-class line. FIX = add `- **Declared work class:** <tiny|story|feature|epic>` to it. *Rec: do now (fold into dev-3's floor-fix PR or a 2-min standalone).* Operator was inclined yes.
- **(5) Merge-gate** — reframed: the merge queue + required reviews ALREADY gate quality (dev-4's #314 self-merge was approved+green → no quality bypass). REAL gap: **all 4 dev seats are repo ADMINS** (can bypass protection + change settings). *Rec: downgrade dev-1/2/3/4 admin→WRITE (least-privilege); drop the controller-only-merge convention (queue is the gate).* **HOLD for Operator's explicit go** (changes fleet access; I can do it via overwatch API).
- **(4) VPS /tmp** — 16G tmpfs 100% full ([[ce-vps-tmp-fills-no-sudo]]; `ce`@VPS has NO passwordless sudo). *Rec: immediate per-seat clean (each seat rm its own stale /tmp — I drive) + ticket for durable host-config (point seat TMPDIR at root disk /215G + tmpfiles.d/cron; root/Operator applies).*
- **My proposed plan (Operator hadn't confirmed before /clear):** execute (6) now + (4)-immediate now; file tickets for (4)-durable + (5); HOLD the (5) admin→write downgrade for explicit go.

## NIGHT ARC #170 — COMPLETE (~21 merges). W1 ✓ · W2 ladder 6/7 (F6.3 #309 pending above) · W3 ✓ FULL (G5#311 · G6 warn-arm#314 · G7 wheel-removal#312 · G8 belt feed#310 canary-clean) · W4 G10#316 ✓ (G9/G11 await #309). Open PRs: ONLY #309.

## ⏰ RE-ARM ON RESUME (session-only crons DIE on /clear):
1. **Watch+route loop** — recreate: CronCreate `17,47 * * * *` recurring, prompt = drive arc per #170 / autonomous-merge approved+green / route seats / execute the #309-land chain above / hold nothing now that Operator is awake (escalate decisions to Operator).
2. **Team-upgrade** — CronCreate `57 16 22 6 *` recurring:false → probe `gh api repos/chmod735-dor/mythos/rulesets`; 200→apply CE floor; 403→notify Operator (fires 22 Jun 16:57 UTC).

## STANDING / AWAITING-OPERATOR
- **Mon 22 Jun ~17:00 UTC GitHub Team upgrade on chmod735-dor** (the Arad gate; cron-verified).
- The 3 ops decisions above (re-surface).

## MEMORIES THIS ARC: [[ce-controllers-proactive-pickup]] · [[ce-codex-seats-cannot-self-compact]] · [[ce-codex-mcp-connector-vs-gh-cli]] · [[ce-belt-feed-polling-default-push-premium]] · [[ce-no-pr-awaits-reviewer]] · [[ce-vps-tmp-fills-no-sudo]].
