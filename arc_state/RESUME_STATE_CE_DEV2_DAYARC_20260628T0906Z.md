# RESUME STATE — CE-DEV-2 Orchestrator — 2026-06-28 ~09:06Z — 7 MERGED; ce244 (relaunch-critical) IN REVIEW

> NEWEST. Open this + MEMORY.md FIRST. Supersedes 0735Z. Dispatch MECHANICS = 0520Z §"PROVEN DISPATCH MECHANISM".
> ⭐ STANDING ROLE: OVERARCHING ORCHESTRATOR — drive via codex controllers, NEVER inline build work. [[ce-dev2-orchestrator-role]].

## AUTH (see MEMORY.md header)
overwatch: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Approve as ce-dev-2: `GH_TOKEN=$(cat ~/.ce-keys/ce-dev-2.pat) gh pr review <n> --approve`. Merge: `gh pr merge <n> --auto` (NO strategy flag — queue sets it). ce-root-v1 = ~/.ce-keys/ce-root-v1{,.pass,.pub}.

## ✅ SHIPPED / MERGED TODAY (28 Jun)
0.3.0 LIVE — tag **release/v0.3.0 → dcbc2d81**. Merged: #604(SSOT preflight) · #605(W2 release-A) · #606(W3 bundle) · #592(W4a AutoReview ARMED) · #603(0.3.0 publish) · **#607(W8 `ce dispatch plan`)** · **#608(W5 G5 body auto-emit)**.

## 🔴 IMMEDIATE ON RESUME — the relaunch path
**#609 = ce244 controller-bootstrap knowledge overlay (ce-ops#344/#244), branch ce244-bootstrap-ssot-overlay, RELAUNCH-CRITICAL.** STATUS (09:10Z): review #1 = REQUEST_CHANGES (1 blocking: AGENTS.md live-path-refusal test gap). **CORRECTION 1 DISPATCHED to dev-1** (brief `.ce/briefs/brief-ce244-correction1.md`): add AGENTS.md test assertion + encode Claude-subagent tiers (Haiku/Sonnet/Opus-controller-only/no-forks) in subagent_model_routing + add acceptance_safety_notes to REQUIRED_SECTIONS + validate ratification_status. dev-1 Working. → ON new push (new head, dismisses review): re-create review worktree (`git fetch origin ce244-bootstrap-ssot-overlay && git worktree add --detach .ce/wt-ce609-review FETCH_HEAD`), re-review (Sonnet reviewer), then on APPROVE + CI green → approve ce-dev-2 + `gh pr merge 609 --auto` (G1; preview-only/additive). **WHEN #609 MERGES: (1) fresh checkpoint, (2) flag Operator GREEN LIGHT to relaunch governed via `ce launch`** (sequence: land ce244 → checkpoint → Operator relaunches Opus/xhigh → resume WITH overlay-load active). #609-review worktree already cleaned (re-create on new push).

## WHY RELAUNCH IS GATED ON ce244 (Operator Q answered this session)
This session = direct `claude` (NOT ce-launched) → no governance/bootstrap injection. Relaunching TODAY before ce244 lands = net-negative (restricts tools WITHOUT the knowledge-load payoff, since #244 injection isn't wired). ce244 slice 1 wires the deterministic controller-knowledge overlay → THEN governed relaunch is pure upside. End-state (later) = CONTAINED governed controller (M2 #207/#208); staged path: governed first, contained second.

## SEATS (live, 09:06Z — all working, parallel-safe disjoint)
- **dev-1** (VPS, NON-contained, tmux `ce-dev1-orchestrator:2.0`): self-pushed #609 (ce244); now effectively idle pending gate. Self-push capable. On #609 merge → conveyor next lane.
- **dev-4** (contained `ce-dgx-codex` local, pane w1:p1): WORKING **ce-342-ci-retrigger** (ce-ops#342, add `edited` to validate.yml pull_request types, tiny, 3 paths). → on READY-FOR-HARVEST: harvest_intake(Sonnet) git-bundle extract → reviewer → gate. ⚠️ dev-4 container FALSELY fails check-examples/well-formed-examples in validate-pr (environmental — passes on host + main CI green); baseline-diff is the regression authority; don't block harvest on it.
- **dev-3** (contained `ce-vps-codex` VPS, `ssh dev1 'sudo docker exec ce-vps-codex …'`): WORKING **W1a/ce-291** (top bet, classify-only) in worktree `/workspace/creator-engine/tmp/ce291-worktree`, branch `ce-291-automerge-classifier-dryrun` (1 commit 164ab98 ahead). Preflight slow (wheel-packaging integration tests, HOURS, NOT stalled — verified xdist workers computing). → on green report: harvest_intake(Sonnet) extract → reviewer → gate → then dev-3 → W6a ce push.

## OPERATOR DECISIONS THIS SESSION
1. PRIORITY = continue engine fan-out (W10 onboarding HELD).
2. NO SEAT IDLE — born-a-foreman; every seat drives multiple file-disjoint tickets; controller ensures parallel-safety via territory-map. [[ce-seats-foremen-self-managed-fanout]]
3. File + dispatch the controller-knowledge-load lane → **ce-ops#344 FILED**; slice 1 = #609 (in flight).
4. Relaunch me governed via `ce launch` AFTER ce244 lands (see above).

## HARD-WON DISCIPLINE (do NOT regress)
1. FULL `ce validate-pr` GREEN in ONE pass before pushing ANY PR (declared-class+floor, path-manifest carrier via `carrier_gen.write_carriers` API, changelog, G5 body line, **+ autogen `.ce/reference/cli.generated.md` via `python scripts/gen_cli_reference.py --write` for ANY new `ce` group** — the new-group coupling is a 3-FILE set: README + test_v1_docs_reconciliation + cli.generated.md). Two-strikes, no whack-a-mole. baseline-diff = the regression gate.
2. G5 body line `- **Declared work class:** <tier>` (floor-satisfying) = FORGE-ONLY gate; body-edit alone won't re-trigger CI → close+reopen (ce-ops#342 fixes this by adding `edited` trigger). A push dismisses approval → re-approve on new head.
3. ALL seat injections (briefs/re-briefs/corrections) = file+pointer+SHA via stdin→tee, never inline. Control-signal confirms (go-push) ok inline. herdr: submit=`send-keys w1:p1 Enter`, read=`herdr pane read w1:p1`; tmux (dev-1) double-Enter past plan-mode hint. Verify landing via `Working` indicator (idle-placeholder capture can be transient — re-read before concluding not-submitted).
4. Every subagent spawn sets `model`: Haiku=mechanical (fleet_recon/ops_triage), Sonnet=substantive (architect_research/implementer/reviewer/harvest_intake), Opus=controller ONLY. ZERO `fork`, ZERO Opus subagents. **EFFICIENCY: author dispatch briefs with a write-capable `implementer`(Sonnet) that writes the file directly — `architect_research` is read-only → forces double-handling the brief in controller (Opus) context.**
5. ⚠️ TERRITORY-MAP incl WORKTREES before dispatch — Haiku recon reports MAIN-checkout branch, MISSES active worktrees (caused the dev-4 dup-W1a near-miss). Verify the actual worktree.
6. HARVEST: contained seats (dev-3/dev-4) → harvest_intake extracts via `git bundle` from the container → host worktree → full validate-pr → push. dev-1 (non-contained) → confirm-to-self-push. Controller holds the gate (review as ce-dev-2 + enqueue); seats never approve/merge.
7. Host /tmp/.git trap: workers use `ce validate-pr` (TMPDIR=/var/tmp hermetic), not raw pytest.

## WATCHERS / HOUSEKEEPING
- Harvest-monitor **/loop armed (ScheduleWakeup ~09:24Z)** — survives /clear; re-enters with full-context prompt. PR-board Monitor persistent. Hourly controller cron.
- **OpenBao wall token: renew before 15:42Z** (G4, ~6h buffer at checkpoint).
- MEMORY.md TRIMMED this session (232→125 lines, 47→24.6KB; backup MEMORY.md.bak-20260628T0745Z); now fully loads.
- ⚠️ Hygiene: dev-4 git remote URL embeds overwatch PAT in plaintext (pane scrollback) — credential-in-URL leak surface; file/fix later.

## QUEUED LANES (conveyor as seats free)
ce244 slice 2/3 (#344 prong 2 checklist content / prong 3 skill-ify ce-dispatch+ce-harvest) · W6a ce push (dev-3 after W1a) · W9 brain (→ host implementer, needs host-local MEMORY/corpus) · W2e/W2f/W6b/W6d = 🔒 (release-tag ruleset / push+self-review brokers).

## ORCHESTRATION LEARNINGS (→ brain W9 / #344)
- Repeated-action knowledge (harvest/dispatch/subagent-config) loads by RECALL not ENFORCEMENT → recurring misses after /clear. Fix = ce-ops#344 (deterministic controller-knowledge overlay via #244 bootstrap injection + skill-ify). This is the relaunch payoff.
- new-`ce`-group coupling is 3 files (README + inventory test + autogen cli.generated.md) — dev-1 W8 STOP-LINE'd correctly on the missing autogen file (my brief-scoping miss; codified into [[ce-new-ce-group-docs-coupling]]).
- contained-seat env can FALSELY fail validate-pr gates (dev-4 check-examples) — verify on host/CI; baseline-diff is the regression authority.
- architect_research(read-only) returning brief text → controller re-writes = double-handling; use implementer to write briefs.
