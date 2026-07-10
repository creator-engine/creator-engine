# RESUME STATE — CE-DEV-2 Orchestrator — 2026-06-28 ~07:35Z — 0.3.0 SHIPPED + TAGGED; W1a LANDING

> NEWEST. Open this + MEMORY.md FIRST. Supersedes 0730Z. Dispatch MECHANICS = 0520Z §"PROVEN DISPATCH MECHANISM" (proven, unchanged).
> ⭐ STANDING ROLE: OVERARCHING ORCHESTRATOR — drive via codex controllers (dev-1/3/4), NEVER inline build work. [[ce-dev2-orchestrator-role]].

## AUTH (see MEMORY.md header)
overwatch: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Approve as ce-dev-2: `GH_TOKEN=$(cat ~/.ce-keys/ce-dev-2.pat) gh pr review <n> --approve`. Merge (queue sets strategy): `gh pr merge <n> --auto --merge`. ce-root-v1 key/pass/pub = ~/.ce-keys/ce-root-v1{,.pass,.pub}.

## ✅ 0.3.0 IS LIVE — DONE
#603 merged 07:17Z (merge sha **dcbc2d81**). Tag **release/v0.3.0 → dcbc2d81 pushed to origin** (annotated, "CE 0.3.0", tag obj 2f61d84c). Verified: docs/downloads/0.3.0/ on main, signed docs/llms-install.md (SSHSIG present). Release milestone complete.

## OPERATOR DECISIONS THIS SESSION (2026-06-28 ~07:45Z)
1. **PRIORITY = continue engine fan-out** (NOT onboarding). W10 onboarding STAYS HELD.
2. **NO SEAT IDLE — born-a-foreman doctrine** (Operator 07:40Z): every seat is a foreman that can/should drive MULTIPLE tickets in parallel as long as parallel-SAFE; controller (me) ensures safety via territory-map. Earlier "hold dev-1" REVERSED → dev-1 dispatched W8.
3. **Let dev-3 land W1a + harvest it** (the active work is W1a in a worktree, not ce-326).
4. **Dispatch discipline reaffirmed**: file+pointer+SHA always (never inline); subagents ALWAYS set model per difficulty (Haiku mechanical/Sonnet substantive/Opus controller-only) — per `.claude/agents/` roles + ce-dispatch skill + dispatch.md playbook. NOTE: architect_research is READ-ONLY → returns brief CONTENT, controller writes the file (matches ce-dispatch SSOT).

## SEATS (live, 07:45Z — ALL THREE WORKING, parallel-safe disjoint paths)
- **dev-3** (contained `ce-vps-codex` on VPS): **WORKING W1a/ce-291** in worktree `/workspace/creator-engine/tmp/ce291-worktree`, branch `ce-291-automerge-classifier-dryrun` — 2 commits (299097a + 2462e56), FULL automerge classifier+policy (forge/automerge_policy.py, mutation_classifier.py, schemas/automerge-*.yaml, tests), preflight running. NOT pushed. ⚠️ MAIN checkout on branch ce-326 — W1a work is in the WORKTREE. → ON COMPLETE: harvest_intake(Sonnet)→reviewer(Sonnet)→HOLD gate→merge. Then dev-3 → W6a ce push (live broker).
- **dev-4** (contained `ce-dgx-codex` on DGX local, pane w1:p1): **WORKING W5/ce-295 slice 1** = G5 PR-body work-class auto-emit (ce-ops#340). Branch `ce-295-w5-g5-body-emit`. Brief `.ce/briefs/brief-ce295-w5-slice1.md` (sha dc130d85, in-container /tmp/brief-ce295-w5.md). Touches ONLY tools/egress-broker/. (Earlier dup-W1a stopped+cleaned.)
- **dev-1** (VPS codex controller, `ssh dev1`, tmux **ce-dev1-orchestrator:2.0**): **WORKING W8/ce-187+#42** = `ce dispatch plan` dry-run planner. Branch `ce187-42-w8-dispatch-plan`. Brief `.ce/briefs/brief-ce187-w8-slice1.md` (sha de173251, in-host /tmp/brief-ce187-w8.md). NEW module dispatch_plan.py + ce_cli.py wiring + tests + inventory guard + README. dev-1 NON-contained (can self-push) but HOLDING for controller gate. Was 12 behind → brief instructs fetch+branch from origin/main.

## 🔴 IMMEDIATE ON RESUME — all 3 seats WORKING; harvest as each reports READY-FOR-HARVEST / pushes
1. **dev-3 W1a** (top bet) preflight done? Probe: `ssh dev1 'sudo docker exec ce-vps-codex bash -lc "git -C /workspace/creator-engine/tmp/ce291-worktree log --oneline -3; ps aux|grep pytest|grep -v grep|wc -l"'` → if done: harvest_intake(Sonnet)→reviewer(Sonnet)→HOLD gate→merge→then dev-3→W6a.
2. **dev-4 W5** (ce-295) — read pane `sudo docker exec -e HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock ce-dgx-codex herdr pane read w1:p1 --lines 15`; harvest when READY-FOR-HARVEST.
3. **dev-1 W8** (ce-187/#42) — read pane `ssh dev1 'tmux capture-pane -p -t ce-dev1-orchestrator:2.0 | tail -15'`; harvest when READY-FOR-HARVEST (dev-1 can self-push but is HOLDING).
4. On each harvest+merge → dispatch next queued lane to the freed seat (born-a-foreman: keep seats loaded). Next: W6a (dev-3), more W5/W8 slices, W9 brain.

## HARD-WON DISCIPLINE (do NOT regress)
- FULL `ce validate-pr` GREEN in ONE pass before pushing ANY PR (incl controller-authored/releases): catches work-sizing-floor, path-manifest carrier (regen via carrier_gen.write_carriers API), changelog carrier, G5 body line.
- G5 PR-body line `- **Declared work class:** <tier>` (floor-satisfying) = FORGE-ONLY gate; body edit alone won't re-trigger CI → close+reopen (ce-ops#342). A push dismisses approval → re-approve on new head.
- ALL seat injections = file+pointer+SHA via stdin→tee (never inline paste/argv). herdr: submit=`send-keys Enter`, clear=`send-keys Escape`, READ pane=`herdr pane read` (NOT `capture`). Verify landing via `Working`/`esc to interrupt`.
- Every subagent spawn sets `model`: Haiku=mechanical, Sonnet=substantive, Opus=controller only.
- ⚠️ TERRITORY-MAP before dispatch: Haiku recon reports MAIN-checkout branch and can MISS active worktrees → verify the actual worktree (caused the dev-4 duplicate-W1a near-miss this session). [[ce-dispatch-territory-map-before-dispatch]].
- Host /tmp/.git trap: tell host workers to use `ce validate-pr` (TMPDIR=/var/tmp hermetic), not raw pytest.

## WATCHERS / HOUSEKEEPING
- **OpenBao wall token: renew before 15:42Z** (G4).
- Token-lean: Operator low on Claude weekly quota — don't over-spawn; codex seats run on GPT pool (separate).
- ⚠️ Hygiene flag: dev-4's git remote URL embeds the overwatch github_pat in plaintext (visible in pane scrollback) — credential-in-URL leak surface; file/fix later.

## QUEUED LANES (dispatch as seats free — dev-1 HELD)
W5/#295 → dev-4 (in prep) · W6a ce push → dev-3 after W1a · W8 forge-triage (HELD with dev-1) · W9 brain → host implementer · W2e/W2f/W6b/W6d = 🔒 (release-tag ruleset / push+self-review brokers).
