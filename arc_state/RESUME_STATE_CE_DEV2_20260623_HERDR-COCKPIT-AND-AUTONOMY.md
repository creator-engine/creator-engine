# RESUME STATE — CE-DEV-2 · 2026-06-23 (PM) · 🏗️ herdr-cockpit build + 2 autonomy programs (parallel)

**WRITTEN BY/WHERE:** CE-DEV-2 controller as `cedev2` on DGX `spark-b824` (GB10 aarch64), cwd `/home/cedev2/creator-engine`, Opus 4.8 effort-high. **SUPERSEDES** RESUME_STATE_CE_DEV2_20260623_INTEGRATOR-AND-REREVIEW.md + PROGRAM_STATE_..._PARALLEL-FORCE-MULTIPLIERS.md. **READ THIS + MEMORY.md FIRST.** Three concurrent programs, all gated, controller holds merge gate. **Every push to a dev MUST embed the foreman preamble** ([[ce-codex-foreman-directive-durable]] standing dispatch rule).

## ✅ MERGED TODAY (origin/main @ b0547afc, moving as #375/#377 land)
#337 forge.re_review (DIFF-AWARE re-review lane — TOP, shipped) · onboarding wave #364–#373 · #370 #371 #372(bot-fix durable) · **#374 Integrator U1 eviction-detection** · **#375 Integrator U2 deterministic resolvers** · **#376 #163 req-2 worker-spawn primitive** · **#378 herdr U1 CE-side scaffold + AGPL boundary**. (origin/main @ 24f949c8)

## 🏗️ PROGRAM 1 — herdr-COCKPIT (THE PIVOT, build this week) [[ce-cockpit-pivot-herdr-base]]
The Cockpit's real need = live/interactive/multi-session agent terminal + governance overlay = herdr's problem space (NOT the read-only Textual viewer, NOT the hand-rolled PTY #368). **Operator-RATIFIED Posture A** (AGPL source-available fork; Python governance = SEPARATE PROCESS over herdr socket, never linked → moat stays proprietary) + **fork supersedes #368**. **Fork-AGPL-firewall ✅ CLEARED by legal.** **aarch64 build ✅** (herdr builds clean on DGX; Rust+Zig 0.15.2; binary at `~/herdr-ce/target/release/herdr`).
- **Fork LIVE: `creator-engine/herdr-ce`** (public, AGPL-compliant: NOTICE+§13+ATTRIBUTION+governance-boundary committed). **Dev clone = `~/herdr-ce`** (durable — NEVER /tmp, [[ce-no-dev-artifacts-in-tmp]]).
- **Units (design `~/ce-ops/designs/DESIGN_COCKPIT_ON_HERDR_20260623.md` + .ce/state/research/ copy):** U1✅(#378 merged) → U2(#379, fix pushed c5026167, dev-4 re-reviewing) → **U3 NEXT** (live `terminal_kind=herdr` VisibilityBackend over socket + RETIRE #368 pty.fork; owner **dev-4**, force-compact it first; build from `~/herdr-ce`) → U4 attribution shim (§7 keystone: steer=attributed `runtime_operator_steer` spine record, fail-closed) → U5/U6 governance overlay + REFUSED feed → U7 CE_DEMO parity (demoable) → U8 A/B/C resizable/interactive/multi-session.
- **REUSE (don't rebuild):** L2 `runner/cockpit_readmodel.py` + Fork-2 refusal seam (`hook_check.py _record_refusal`) + `cockpit_demo_seed.py` port as the overlay; only L3 is rebuilt on herdr. Textual cockpit (v3_cockpit.py, B.1-B.6 BUILT, 146 tests) = learnings/L2 donor, frozen.
- **INVARIANT:** keep Python governance a separate process over the socket (legal clearance depends on it); control socket owned by CE substrate, never the governed seat (U2 #379 pins this §7 invariant).
- **NVIDIA pitch = SEPTEMBER** (the "01-Jul" in cockpit doc/#74 is a stale demo-milestone). Eval ticket **ce-ops#217**.

## 🤖 PROGRAM 2 — Integrator MVP (autonomous merge-mechanics, ce-ops#216) — dev-1 foreman
Phase-1 deterministic-only. U1 #374✅merged. **U2 #375 resolvers = APPROVED+enqueued (landing).** **dev-1 driving U3 (executor+race-guard: read-only resolver→executor holds write, race-guard re-checks head SHA) + U4 (escalation seam: non-mechanical→controller, never silently park).** Mandate: `.ce/state/research/BUILD_MANDATE_INTEGRATOR_MVP_20260623.md`.

## 🦾 PROGRAM 3 — #163 born-a-foreman (deterministic foreman-fanout) — dev-4 foreman
DESIGNED+ratified (hard-deny modeled §7 push-block; trigger action-type×irreversibility; worktree+cred-scrub). req-2 worker-spawn #376✅merged. **dev-4 driving req-1 (born-a-foreman launcher inject) + req-3 (§7 hard-deny refusal; route refusals through `_record_refusal` → cockpit feed).** Prereq #148 = #377 (provisioning) landing. This program is the durable enforcement of the foreman dispatch rule.

## 🔴 LIVE BOARD (gate: reviewDecision==APPROVED on CURRENT head + green + CLEAN → `gh pr merge <n> --auto` no --squash; queue handles BEHIND)
- **#379 (herdr U2 containment) APPROVED+CLEAN+ENQUEUED → landing → UNBLOCKS herdr U3.**
- #377 (#148 provisioning) REVIEW_REQUIRED — its conflict-resolving rebase (head 0d8fae78, CI green) reset the approval; **dev-1 re-approve DISPATCHED** → auto-merge fires on approve. (This manual re-approve toil = the exact case forge.re_review Phase-2 live-wiring + the Integrator eliminate.)
- **#380 (Integrator U4 escalation-seam, author dev-1) REVIEW_REQUIRED + DIRTY** → route review (non-dev-1) + needs rebase.
- **#381 (#163 req-1 born-a-foreman-inject, author dev-4) REVIEW_REQUIRED** → route review (non-dev-4).
- IN-FLIGHT (PRs pending): dev-1 → Integrator U3 (executor+race-guard) · dev-4 → #163 req-3 (§7 hard-deny) · **dev-4 → herdr U3 (dispatch once #379 lands; force-compact dev-4 first; build from `~/herdr-ce`; retire #368 pty.fork).**
- Parked Track C: #349 (live-site APPROVED ⏸️Operator visual-check) · #351 (mint-broker CHANGES_REQUESTED) · #362 (docs).
- Disjoint modules → parallel-mergeable; serialize only shared `_versions.py`/`test_version_boundary.py`.

## 🖥️ MECHANICS / REACH
- dev-4=`ssh cedev4@localhost -i ~/.ssh/id_ed25519` (tmux `dev4stage1:0.0`, ~/ce-workspaces/creator-engine) · dev-3=`ssh dev3` (`dev3-onboard:0.0`, ~/creator-engine) · dev-1=`ssh dev1` (`ce-dev1-orchestrator:controller`, ~/creator-engine). codex gpt-5.5 high. Dispatch: `cat brief | ssh <h> "tmux load-buffer -b ce -; tmux paste-buffer -p -b ce -t <pane>; sleep 0.3; tmux send-keys -t <pane> Enter"`. **Every brief leads with the foreman preamble.**
- overwatch gh: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. **PAT now has `administration`** (Operator granted) → can fork/create repos. ce-ops sync: `cd ~/ce-ops && ./sync-ops.sh "msg"`. Rust toolchain durable in `~/.cargo`+`~/.rustup`.
- Work-class line MUST be bare bold `- **Declared work class:** <tiny|story|feature|epic>` (code-span/missing → G5 FAIL; body-edit alone won't re-trigger CI — needs a push/rebase). [[ce-pr-work-class-line-format]]

## 🆕 TODAY'S DURABLE DECISIONS (memories)
[[ce-cockpit-pivot-herdr-base]] · [[ce-rent-or-fork-before-reinvent]] (herdr=fork; build only differentiator; CHECK FIRST even own repo) · [[ce-orchestration-replaces-model-upgrade-pitch]] (MOAT: wk-21Jun orchestration surpassed Fable-upgrade peak, SAME model — GH Insights) · [[ce-agent-paced-estimation]] (5th reinforcement: single leg = minutes-to-hrs NEVER days; stop human-pace skepticism) · [[ce-codex-foreman-directive-durable]] (standing dispatch rule: embed foreman preamble every push) · [[ce-no-dev-artifacts-in-tmp]] · [[ce-integrator-merge-mechanics-agent]].

## 📋 NEXT-SESSION FIRST ACTIONS
1. **TOP: when #379 merges → dispatch herdr U3 to dev-4** (force-compact dev-4 first; build from `~/herdr-ce`; live `terminal_kind=herdr` VisibilityBackend over socket + RETIRE #368 pty.fork). Brief embeds foreman preamble + durable-path rule. Then U4 (attribution shim §7 keystone).
2. Confirm dev-1 re-approved #377 → it auto-merges (#163 prereq lands).
3. Route reviews (non-author, foreman preamble): **#380** Integrator U4 (non-dev-1; needs rebase first — DIRTY) · **#381** #163 req-1 (non-dev-4). Collect dev-1's Integrator U3 PR + dev-4's #163 req-3 PR as they open; enqueue each green+approved (disjoint → parallel).
4. **Near-term unit: forge.re_review Phase-2 live-wiring** — auto-fast-clear base-only rebases (kills the manual re-approve toil seen on #373/#377); rides the Integrator lane, no dup. [[ce-integrator-merge-mechanics-agent]]
5. Dual-write this resume to CE-DEV-1 + ce-ops (done this session via sync-ops).
