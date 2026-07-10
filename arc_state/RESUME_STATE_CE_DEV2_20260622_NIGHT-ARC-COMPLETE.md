# RESUME STATE — CE-DEV-2 · 2026-06-22 ~02:25 UTC · NIGHT ARC #170 ESSENTIALLY COMPLETE → MORNING DECISIONS PENDING

**WRITTEN BY/WHERE:** CE-DEV-2 controller as `cedev2` on the **DGX `spark-b824`**, cwd `/home/cedev2/creator-engine` on `main`, Opus 4.8 effort-high. SUPERSEDES `RESUME_STATE_CE_DEV2_20260621_NIGHT-ARC-UNATTENDED.md`. Read this + MEMORY.md first. **main ≈ d1720857** (+ #312 merging → 21 merged).

## PEER-SEAT → HOST → REACH (unchanged): dev-1 `ssh dev1` %0 · dev-3 `ssh dev3` %2 · dev-4 `ssh cedev4@localhost -i ~/.ssh/id_ed25519` dev4stage1:%0. overwatch gh: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. ce-dev-2 PAT `~/.ce-keys/ce-dev-2.pat`.
- **⚠️ VPS scp BROKEN — /tmp tmpfs full.** Send VPS nudges via: `cat localfile | ssh devN 'cat > ~/f.txt'` then send-keys from `~/f.txt`. NOT scp to /tmp.

## 🌙 NIGHT ARC #170 — DELIVERED ITS AUTONOMOUS SCOPE (~21 merges)
**Merged tonight (incl. day):** queue#301 · belt#302 · mint-broker#300 · F-wheel-1#299 · brain ladder F1#298/F2#304/F6.1#306/F6.2#307 · trust-anchor#294 · F4#305 · F3#308 · #303 · G5 work-sizing#311 · belt-types#313 · G6 warn-arm#314 · G10 test-health#316 · 422-guard#317 · path-manifest#318 · forge-plan#319 · windows-ws#320 · belt-claim-fix#321 · **G7 wheel-removal#312 (enqueuing)**.
- **W3 deterministic substrate COMPLETE:** G5 ✓ · G6 ✓ (warn-arm) · G7 ✓ (#312) · G8 belt feed ✓ + **CANARY-CLEAN** (3 bugs caught+fixed: 422 #313, test-guard #317, claim-crash #321).
- **W4:** G10 ✓. G9 (brain smoke) + G11 (brain MCP server) **BLOCKED on #309**.
- **Brain ladder 6/7** — F6.3 #309 **PARKED** (see below).

## ⏸️ MORNING DECISIONS FOR OPERATOR (6)
1. **#309 (F6.3 recall) — work-sizing-floor block.** +1609 lines: too big for `feature`, not structured as `epic`. All code findings fixed + 128 tests pass; SIZE is the only blocker. Options: (a) split into bounded sub-PRs, (b) restructure as epic w/ artifacts, (c) one-time override, (d) confirm floor should exclude test lines. **Unblocks F6.3 + G9 + G11.** (posted on #309)
2. **G6 enforce-flip** — seat_class is WARN-armed (#314 merged); flipping to ENFORCE is the staged checkpoint (HELD).
3. **G8 belt launch-arm** — belt is canary-clean + ready; arming `--enable-launch` is the staged checkpoint (HELD). This is the deterministic-pickup go-live.
4. **VPS /tmp cleanup + cron** — 16G tmpfs 100% full; I can't fully clean (no passwordless sudo). [[ce-vps-tmp-fills-no-sudo]]
5. **Deterministic merge-gate** — dev-4 self-merged #314 despite the no-self-merge directive; prompt-level rule unenforced → needs a ruleset (merge restricted to overwatch/controller). 
6. **G5 PR-template** — the work-sizing gate now requires `- **Declared work class:** <class>` on every PR; new PRs need a template carrying it.

## SEATS (terminal): all idle/winding down — no unblocked work left (G9/G11 await #309). dev-4 = workhorse (built G7 + #318/319/320 forge PRs). Codex auto-compacts; don't panic-restart.
## CRONS: 95feba1b (night-arc loop :17/:47) · 70fb7852 (Team-upgrade 22 Jun 16:57 UTC). 
## STANDING: Mon 22 Jun ~17:00 UTC GitHub Team upgrade on chmod735-dor (the Arad gate).
## MEMORIES THIS ARC: [[ce-controllers-proactive-pickup]] [[ce-codex-seats-cannot-self-compact]] [[ce-codex-mcp-connector-vs-gh-cli]] [[ce-belt-feed-polling-default-push-premium]] [[ce-no-pr-awaits-reviewer]] [[ce-vps-tmp-fills-no-sudo]].

## ✅ RATIFIED 2026-06-22 (Operator, post-wake)
- **Work-sizing floor fix: EXCLUDE test LOC** — dev-3 (G5 author) building it (governed PR). Floor sizes on SOURCE LOC only; tests no longer penalize sizing.
- **#309 (F6.3): GRANDFATHER/land** once the floor-fix merges. If source-only (834) clears `feature` → passes legitimately; else documented pre-gate override. Then enqueue (code-approved, 128 tests green) → unblocks F6.3 + G9 + G11 + ladder 7/7.
- **G6 enforce-flip + G8 belt launch-arm = BATCH, gated on #309 LANDING.** Controller executes BOTH the moment #309 merges — NO further ask. (G6: flip seat_class hook_check.py warn→enforce. G8: deploy belt poll+claim with `--enable-launch` ON.)
