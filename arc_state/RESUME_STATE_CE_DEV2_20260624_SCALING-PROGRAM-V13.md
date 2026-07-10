# RESUME STATE — CE-DEV-2 · 2026-06-24 PM · 🏗️ 12-HOUR SCALING PROGRAM → PRE-DAWN RELEASE · V13

**WHERE:** CE-DEV-2 controller, `cedev2` on DGX `spark-b824` (GB10 aarch64), cwd `/home/cedev2/creator-engine`, Opus 4.8 high. **SUPERSEDES V12** (V12 still holds the contained-seat dispatch pipeline detail + container paths — read it for ops mechanics). READ FIRST: this + MEMORY.md + [[ce-release-to-traction-doctrine]] + [[ce-parallelize-everything-scale-the-gate]]. Discipline unchanged: **verify-don't-trust**, **build properly (quality never compromised)**, **codify don't rediscover**. Designed to survive MULTIPLE context clears.

## 🎯 THE MISSION (next ~12h, Operator-set 2026-06-24 PM)
Tomorrow (2026-06-25) we onboard FIRST TEST USERS (Arad + others) **and** contributors — this is a GIVEN. But install+onboard is the PAYLOAD, not the work. **Primary deliverable of the next 12h = scale CE dev capability MASSIVELY**; the scaled machine then lands install+onboard at **pre-dawn**.
- **THE MENTAL SWITCH:** no more sequential work. Controller = FOREMAN. The ENTIRE plan is composed to PARALLELIZE. Every seat drives MULTIPLE lanes at once (reviewing is ONE lane for dev-1/dev-2, they don't sit idle as "reviewers"). **Build properly** — parallelism does NOT lower quality. [[ce-parallelize-everything-scale-the-gate]]
- **Strategy:** release-to-traction (OpenClaw/NanoClaw playbook), quality-where-it-counts, DoD-gated release. [[ce-release-to-traction-doctrine]]

## 🏗️ THE SCALING PROGRAM (ordered, gated — the spine of the 12h)
**Headline from the scaling-readiness audit: the scaling infra is BUILT but NOT RUNNING.** Only running = a do-nothing 5-min cron poll + ME serially. So this is **activation + getting the controller OUT of the serial loop**, not construction. **Core principle: scale the GATE before/with the WORKERS** (pipeline scales at its weakest link, which moves as you scale).

- **PHASE 0 — turn on the gate (current 3-wide, NO concurrency bump yet). Prereq to everything.**
  - ✅ **Autonomous grader: RESOLVED** — CI already runs the FULL pytest suite offline (`.github/workflows/validate.yml:50` "Creator Engine validator — pytest suite") + carrier gate (#410). → **STOP hand-running host-side pytest; trust CI.** (Tradeoff: a broken seat-push burns a CI run vs my pre-verify — acceptable; optional seat-venv pre-check later.)
  - ✅ **Integrator merge daemon — LIVE** (#426+#428 merged, main `559c4198`). Running `--loop` on DGX (pid via launcher), token=overwatch. Verified: code review + unit tests + LIVE dry-run gating of real PR #428 (skip review_not_approved→approval_not_current_head→rollup_not_success, never merged unqualified). THE gate-scaler. **Operator nod GRANTED + condition met → flipped live 2026-06-24 PM.**
  - ✅ **Review-pickup daemon — LIVE** (#427 merged). Running `--loop --apply`, identity ce-dev-2, seat pool ce-dev-1/3/4. Verified live-clean.
  - 🚀 **LAUNCHER (codified):** `~/.ce/bin/launch-gate-daemons.sh` — idempotent relaunch of BOTH daemons from SOURCE (installed cev3 stale, #198), pre-flight asserts the discovery query is balanced + synced to origin/main. Logs `~/.ce/logs/{integrator,review}-daemon.log`. ⚠️ daemons are nohup (survive session, NOT reboot) → systemd-ize as hardening.
  - ⬜ **Worktree-isolated dispatch:** route fan-out through `worker_spawn.py` (#163) worktrees + `work_claims.py` (#38/#200) lanes — built, NOT on the dispatch path today (codex runs in SHARED `/workspace` → collision at scale). QUEUED.
  - ⬜ **Auto carrier-gen + PR-open** as a belt/seat step (today I run `/tmp/gen-manifest.py` + `gh pr create` by hand). QUEUED.
  - **EXIT GATE:** one PR flows **brief→merge with ZERO manual steps from me.**
- **PHASE 1 — ramp 3→5.** Set codex concurrency (key below), bounded fan-out. **GATE:** 5 lanes sustain, no human intervention, no quality slip.
- **PHASE 2 — 5→8.** Only after 5× holds; FIRST fix **Search-API 30/min** cap (App-installation tokens / stagger+cache polls) + observability at volume. **NEVER above 8.**
- **PHASE 3 — pre-dawn:** run the install+onboard RELEASE DoD on the scaled machine.
- **Assessment:** I assess readiness each notch; **Operator ratifies each step-up.**
- **🔑 AUTHORITY FLAG:** Phase 0 makes the gate merge AUTONOMOUSLY (approved+green+carrier-pass, fail-closed = pre-authorized belt-merge). **BUILD the daemons now; gate FLIPPING THEM LIVE on (a) my verification they're fail-closed + (b) a quick Operator nod.**
  - ✅ **NOD GRANTED 2026-06-24 PM** — conditional ONLY on (a) my fail-closed verification. Per-daemon bar: must REFUSE on (i) stale approval on old head, (ii) CI/carrier not SUCCESS on current head, (iii) non-mergeable/draft; merge/route ONLY when all-green on the CURRENT head. Once verified → I flip live + report "verified" to Operator. **No further nod needed.**

## ⚙️ CODEX CONCURRENCY (verified, binary + official docs)
- Key: **`[agents] max_threads`** in `~/.codex/config.toml` (=`$CODEX_HOME/config.toml`). **GLOBAL** cap (total concurrent agent threads, not per-thread). Or per-invocation `-c agents.max_threads=N`. No CLI flag.
- **Documented default = 6** — ✅ VERIFIED on dev-4: NO `max_threads` key set → seats already run at default 6. **CALIBRATION RESOLVED (Operator 2026-06-24 PM):** ramp is **6→8, NEVER above 8** (not 3→5 — that assumed default 3).
- **🔑 PRINCIPLE — MAX OUT THE DEFAULT FIRST (Operator 2026-06-24 PM):** we are NOT even using what codex gives us by default. Serial single-brief dispatch leaves **~5 of 6 threads idle per seat.** So the FIRST scaling milestone = **SATURATE the default 6** — via foreman fan-out (dispatch a *decomposable objective* → thread-per-piece → sub-agents, NOT one build brief) + **worktree-isolation** (the collision-safe prereq, since 6 real builds in one shared `/workspace` would clobber each other). ONLY after default-6 is saturated AND the gate runs itself do we set 6 explicit → prove → 8. **Bumping the cap while threads sit idle is meaningless.**
- Prereq `multi_agent` feature: **already stable+true on DGX** (verify on dev-1/dev-3 hosts before their ramp: `codex features list`).
- **`agents.max_depth` default 1** (sub-agents can't spawn their own). The Operator's "10 threads × 20 sub-agents each" vision needs depth≥2 (recursive) — **Phase-1 calibration decision: keep depth=1 first (one fan-out level), assess, then consider 2** (runaway risk). Keep job timeout default 1800s.
- **Caveat:** each thread = full model inference → N× token burn on the SHARED OpenAI weekly pool ([[ce-codex-shared-account-subscription]]). Cap is a ceiling not a target.

## 🚦 RELEASE DoD (for Phase 3 / pre-dawn) — ✅ RATIFIED 2026-06-24 PM
Gate rule: every must-have passes its probe (evidence, no self-report); any blocker open → **slip, don't ship.** Target tag **v0.3.0 pilot** on pass ([[ce-semver-milestone-policy]]). Recorded on ce-ops#191 as the durable gate.
- **D1** clean-room install, zero undocumented manual steps · **D2** first-value workflow end-to-end on the INSTALLED `ce`/`cev3` · **D3** quickstart gets zero→first-value unaided · **D4** auth + shared App install on target repo · **D5** unhappy paths fail-closed+informative, no data loss/secret leak · **D6** contributor onboarding (access+setup+first contribution).
- **DEFERRED (not gating tomorrow):** full gVisor/herdr contained controllers (ce-ops#230), `ce update` (#190), WebUI, agent-pointed install (unless chosen as modality).

### Install rehearsal findings (BANKED — clean-room ubuntu:24.04, the D1/D2/D3/D5 probe)
Install MACHINERY is SOLID (#223 auto-remediation of ssh-keygen/uv/python3.14 ✅, signed-spec + DNS-TXT trust ✅). **3 BLOCKERS:** (1) stock Ubuntu lacks **curl** (one-liner can't run; undocumented); (2) **git** not pre-checked/remediated → install CRASHES with raw traceback at inventory; (3) quickstart commands (`ce onboard/session/ratify/drive/merge`) **don't exist on installed binary — they're `cev3`**. FRICTION: README overstates installed `ce` surface (#198 made concrete), `ce` not on PATH same-shell (need re-source), `ce doctor` FAILs on installed host (looks for source paths), one-liner exits non-zero on optional-inventory fail, quickstart not linked from homepage. **Shortest path to yes: doc fixes (curl+git prereq note; ce→cev3 in quickstart) + git auto-remediation in install.sh.** If we pre-provision the user's host with curl+git, blockers 1&2 evaporate.

## ✅ ALL OPERATOR DECISIONS RESOLVED (2026-06-24 PM) — nothing pending
1. ✅ **6-criterion release DoD RATIFIED** (D1–D6 + must-have/deferred split as drafted).
2. ✅ **`ce` vs `cev3`: RATIFIED doc-fix to `cev3`** for tomorrow + track unification (#198) post-release (NOT the shim).
3. ✅ **Concurrency: RESOLVED** — ramp 6→8, never >8; saturate default-6 first (see CODEX CONCURRENCY).
4. ✅ **Gate-live nod GRANTED** (conditional on my fail-closed verification — see AUTHORITY FLAG).

## 🎯 ONBOARDING SPEC — Arad (she/her), tomorrow 2026-06-25 (parameterizes D2/D4/D6)
- **Q1 WHERE:** Arad's own **fresh Ubuntu 24.04**, with **Claude Code already installed + authed**. **Assume NO other CE deps** (no curl/git/uv/python guaranteed) → this is EXACTLY the install-rehearsal blocker surface (curl-missing, git-missing-crash). The rehearsal's clean-room target = her real machine.
- **Q2 MODALITY:** **team-mode, brownfield, mythos repo** (same as last attempt). Repo = **https://github.com/chmod735-dor/mythos**; we own the org + repo; **Arad = co-owner w/ Admin creds**. CE-side access = **`~/.ce-keys/mythos-overwatch.pat`** (login `ce-overwatch`, org+repo highest perm). Install via **one-liner OR Agent-pointed** (point her Claude-Code TUI at the **signed playbook**). ⚠️ Last attempt the Agent install **proceeded then hit HARD STOPS** on unanticipated blockers (= the rehearsal findings: curl/git prereqs, ce→cev3 docs).
- **Q3 FIRST-VALUE (the "wow" to bulletproof):** ONE successful **end-to-end gate**: **author → commit → push → PR → merge** on mythos.
- **Q4 CONTRIBUTOR:** selected from the **waiting list AFTER Arad's successful onboarding**; "onboarded" = CE installed on her machine (one-liner or Agent-pointed) + Q3 gate passes. Who = TBD post-Arad.
- **SEQUENCING (unchanged):** do NOT pivot the fleet now. Scale the pipeline (Phases 0→2) through day+night; the scaled fleet closes the DoD-blockers and runs the N6 rehearsal gate **at pre-dawn**. These answers PRE-PARAMETERIZE that pre-dawn payload.

## 🔧 IN-FLIGHT (verify/resume these first) — updated 2026-06-24 PM
- **review-pickup daemon (#427, MERGED `fada8c70`): ✅ VERIFIED LIVE-CLEAN** — live `cev3 review-pickup --identity ce-dev-2 --repo creator-engine/creator-engine --seat ... --once --dry-run` ran the real search path, 0 awaiting PRs, no error. **Banked; ready to flip live (`--loop --apply` with seat pool) — flip together with Integrator.**
- **Integrator daemon (#426, MERGED `b8d9c921`): NOT live yet — 2 live-only bugs in `discover_daemon_candidates`** (CI green because unit tests inject `candidates=` and never build the live gh call):
  1. `_gh_graphql` passed a variable named `query` → collided with gh's reserved `query=` doc field. FIXED by dev-4 `aa5a254` (rename `$query`→`$searchQuery`).
  2. `_DAEMON_SEARCH_QUERY` brace-unbalanced (21 `{` vs 22 `}`, extra trailing `}`) → gh parse error. **Controller verified the 1-brace fix LIVE (dry-run then clean).** dev-4 **iter-2** in flight on branch `ce-integrator-discovery-fix` (apply brace fix + add offline query-validity test).
  - **NEXT:** dev-4 iter-2 commits → I re-run live dry-run → **open the iter-2 PR → run the daemon dry-run against THAT real PR** (it should SKIP it pre-approval/pre-carrier with a correct reason = the real behavioral gate proof) → carrier/PR/review (ce-dev-2, dev-authored) → land → **flip BOTH daemons live + report "verified + live" to Operator** (pre-authorized).
  - ⚙️ RUN DAEMONS FROM SOURCE: `.venv/bin/cev3` is a STALE install (missing queue-daemon/review-pickup/queue-poll). Invoke `PYTHONPATH=validators .venv/bin/python -m creator_engine_validator.v3_cli <cmd>` (token via `GH_TOKEN`=overwatch). #198 dogfooding gap.
- **dev-1** (VPS tmux `ce-dev1-orchestrator:2.0`): driving **#228 cred-injection design**.
- 🧠 **LEARNING (bank → process):** daemons/forge code that calls REAL gh/GraphQL APIs need a **live smoke-test gate** before "done" — mocked-discovery unit tests passed CI but hid 2 live-only bugs. The live dry-run IS the grader-outside-the-agent. Add a live smoke-test to the daemon DoD (Phase-0 hardening).
- **Worktrees open:** `/home/cedev2/ce-wt/{integrator,review,discovery-fix}` (clean up post-land via `git worktree remove`).

## ✅ LANDED THIS SESSION (main tip `e3efb3a3`)
8 PRs merged: #416 (codex hook redact), #419 (Wave-A: Ring-1 hook reg in contained config + tests), #420 (#229 live-action scope guard), #421 (Wave-B: herdr send-keys Enter + sha256 deliver), #422 (#174 path-manifest live-base/stale-rerun), #423 (#223 install prereq auto-remediation), #424 (Wave-C: canary fixes), #425 (App-grant fail-closed). **All 3 Phase-1 security quick-wins DONE** (API-classifier #418 prior, App-grant #425, Ring-1 hook via Wave-A). Canary ran twice (caught+drove real bugs). Tickets filed: ce-ops#230 (parked Wave-D canary-completion + crit-6 **agent-reaction verification RATIFIED** + born-foreman follow-ups).

## 🛠️ OPS ESSENTIALS (carry forward; daemons SUPERSEDE the manual pipeline post-Phase-0)
- **Containers:** dev-4 `ce-dgx-codex` `/workspace/creator-engine`=host `/home/cedev4/ce-workspaces/creator-engine`, CODEX_HOME `/home/cedev4/.codex`. dev-3 `ce-vps-codex` `/workspace/creator-engine`=host `/home/ce-dev-3/creator-engine`, CODEX_HOME `/home/ce-dev-3/.codex` (via `ssh dev3`).
- **Dispatch (current, being automated):** brief→`tee /tmp/brief.md`+md5-verify→`codex exec --dangerously-bypass-approvals-and-sandbox "$(cat /tmp/brief.md)"`→verify commit in container→**Model-B push from HOST** (dev-4 `ssh cedev4@localhost -i ~/.ssh/id_ed25519 'cd ~/ce-workspaces/creator-engine && git push'`; dev-3 `ssh dev3 'cd /home/ce-dev-3/creator-engine && git push'`)→fetch (STALE-REF: `git fetch origin 'refs/heads/X:refs/remotes/origin/X' --force`)→**rebase onto current main**→host test under `TMPDIR=/home/cedev2/cetmp` w/ `.venv/bin/python`→carriers→PR→review→`gh pr merge --auto` (NO --squash). NOTE: don't run codex exec with trailing `&` (loses completion signal).
- **Carriers** ([[ce-carrier-verify-require-carrier-gap]]): write changelog → COMMIT it → `/tmp/gen-manifest.py <slug> <issue> <title>` (AFTER commit) → commit manifest → `verify-path-manifest --base origin/main --manifest-dir .ce/pr-manifests --head-ref <slug> --require-carrier` (PASS) → push. Body needs `- **Declared work class:** <story|feature|...>`.
- **Review routing:** dev-authored PR → I review as ce-dev-2; ce-dev-2-authored → dev-1. Force-push staleness re-reviews approval → re-approve on new head. [[ce-dismiss-is-not-approve]]
- **Tokens:** `~/.ce-keys/ce-dev-2.pat`; overwatch `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Repo `creator-engine/creator-engine`; ISSUES `creator-engine/ce-ops`. Forge headroom: core ~5000/hr/identity OK; **Search-API 30/min = the scale cap** (Phase 2).

## 🎛️ CONTROLLER QUEUE (fresh-me, in order)
1. **Resume Phase 0:** poll/verify dev-4 Integrator daemon + dev-3 review daemon builds → pipeline them → verify fail-closed → **get Operator nod → flip the gate live.**
2. **Finish Phase 0:** worktree-isolated dispatch (worker_spawn+work_claims) + auto-carrier+PR; STOP hand-running pytest (trust CI). Prove EXIT GATE (one PR brief→merge zero-touch).
3. **Get the 5 pending Operator decisions** (above) — they unblock Phase 1 calibration + Phase 3.
4. **Phase 1:** set `[agents] max_threads` (calibrated), bounded fan-out, assess.
5. Keep dev-1 on #228; every seat multi-lane (no single-role idling).
6. **Phase 3 pre-dawn:** drive the release DoD (N1 git-remediation + soft-fail inventory + re-source; N2 docs curl+git + ce→cev3 + homepage link; N3 first-value script; N4 auth probe; N5 fail-safe; N6 re-run clean-room rehearsal = the gate). Ship IFF green.
