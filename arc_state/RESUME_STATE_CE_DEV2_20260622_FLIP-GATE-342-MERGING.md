# RESUME STATE — CE-DEV-2 · 2026-06-22 ~afternoon · Flip gate #342 merging; CORRECTED flip mechanism

**WRITTEN BY/WHERE:** CE-DEV-2 controller as `cedev2` on the **DGX `spark-b824`** (dgx-spark-1/100.100.105.50, GB10, aarch64), cwd `/home/cedev2/creator-engine`, Opus 4.8 effort-high. SUPERSEDES `RESUME_STATE_CE_DEV2_20260622_AUTONOMY-FLIP-PENDING-195.md`. **Read this + MEMORY.md first.** origin/main ≈ `e63fde14`.

## PEER-SEAT → HOST → REACH
- THIS host = DGX. dev-1 `ssh dev1` (tmux `ce-dev1-orchestrator`) · dev-3 `ssh dev3` (tmux `dev3-onboard`) [VPS] · dev-4 `ssh cedev4@localhost -i ~/.ssh/id_ed25519` (tmux %0) [DGX]. cedev2 + dev-1/dev-3 run the validator via `cd ~/creator-engine && PYTHONPATH=validators python3 -m creator_engine_validator.ce_cli …` (NO `ce` on PATH — dev-1/dev-3 have no `ce` at all; only dev-4 has installed `ce`).
- overwatch gh: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. ce-dev-2 PAT `~/.ce-keys/ce-dev-2.pat`. Force-push quirk: `--force-with-lease` errors "stale info" until you `git ls-remote origin <branch>` and pass the explicit `--force-with-lease=<branch>:<remoteSHA>`.
- ISSUE TRACKER = creator-engine/ce-ops (private). CODE/PRs = creator-engine/creator-engine.

## 🎯 AUTONOMY FLIP — CORRECTED MECHANISM (supersedes prior resume's dev-4-canary framing)
- **The belt cron runs from SOURCE via `python -m`, NOT the installed `ce`.** Live cron on cedev2 + dev-1 (and dev-3): `3-59/5 * * * * bash -lc "cd ~/creator-engine && PYTHONPATH=validators python3 -m creator_engine_validator.ce_cli pickup poll --identity ce-dev-N --allow-ambient-gh --repo creator-engine/creator-engine" >> ~/belt-canary.log  # CE-BELT-CANARY` (READ-ONLY: polls the CODE repo, no --claim/--enable-launch).
- **⇒ The #340 launch-argv fix reaches the belt by UPDATING each cron host's `~/creator-engine` checkout to main. NO publish/wheel/`ce update` dependency.** The stale installed `ce` on dev-4 (build `0.2.0+ac513c4f`, #225-era, pre-#338/#340) is a **RED HERRING for the flip** — relevant only to the Arad/Release&Update track (#190 `ce update`), not the dev-fleet flip.
- **Prior bare-`ce` canary failure is FIXED by #340** (`build_lane_argv` now emits `[sys.executable,"-m","creator_engine_validator.ce_cli","lane","launch",…]`), so the canary can run via `python -m` from ANY updated checkout — including cedev2 (observable here).
- **FLIP = (1)** `git -C ~/creator-engine pull` to current main on each cron host (dev-1, dev-2, dev-3); **(2)** rewrite the CE-BELT-CANARY cron line to the claim form: `… pickup poll --identity ce-dev-N --repo creator-engine/ce-ops --label ce-pickup/triage-ready --claim --enable-launch --harness codex --seed-root ~/ce-belt/seeds --repo-root ~/ce-workspaces/creator-engine --lane-ledger-root ~/ce-belt/lanes` (create the belt roots first; verify exact flag names against `pickup poll --help`). NOT the cedev2 controller (no self-launch).
- **CANARY (do FIRST, after #342 lands):** run the claim-form command ONCE scoped to a single item, observe a governed lane spawn, tear it down (`… claim release <n> …`). Then report → get Operator GO for the actual cron rewrite (flip = highest-consequence binding act; canary is pre-authorized, the fleet cron-rewrite needs the go).

## SEQUENCING (Operator directive 2026-06-22): hold flip until #196 (#342) lands → canary → (go) → flip.
- **#342 (#196 queue-hygiene completeness = FLIP GATE)** — APPROVED by dev-1 (it authored #194 this extends), Validate green, **in merge queue** (monitor beotmpgdt). It adds fail-closed exclusion of done-but-open (merged linked PR) / held (AWAITING-OPERATOR/⏸ body+comment) / meta-debug. Built by the CONTROLLER's own build worker (the new mode: controller drives its own lane via workers, not just routes). Authored ce-overwatch.
- On #342 merge: pull main here → run the one-item canary → report → flip on go.

## BOARD (creator-engine PRs)
- **MERGED today:** #322 #309 #323 #327 #329 #331 #332 #338(#194 hygiene) #340(#195 launch-argv) #339(#192 CI) #333(broker Slice-1) #334(#173 reinstall). #342 merging.
- **OPEN:** #342 (merging) · #343 (NEW — a seat self-picked work; REVIEW_REQUIRED — triage who/what + route review) · #337 (mine #151 reconciler, CHANGES_REQUESTED/BEHIND — rebased+pushed earlier, needs CI-green + dev-4 re-approve; the conservative auto-dismiss rule is the substance) · #335 (dev-4 #80 signed-publish, CHANGES_REQUESTED, dev-4 fixing).

## SEAT BEHAVIOR (the real long pole for "every dev independent")
- All 3 seats **burst-then-idle**: do one unit, return to the idle smart-suggest prompt (grayed ›). The AGENTS.md proactive-pickup loop is NOT holding. dev-3 hit 14% context (auto-compacts near limit — don't panic-restart). dev-1 auto-compacted 31%→77%. ⇒ Controller still nudges every push→review→merge hop. This durability gap — a belt-LAUNCHED seat must drive its claim to a green PR unattended — is the true gate on hands-off autonomy, only partly ticketed (#151 reconciler #337 + #188 reviews-pickup). The honest acceptance test = watch ONE fully-unattended claim→PR cycle succeed before calling autonomy "live".

## TASKS (TaskList): #1 land #340→canary→flip (BLOCKED by #3) · #2 drive fix-cycle PRs · #3 land #196/#342 (in_progress, FLIP GATE).

## ⚠️ OPEN STRATEGIC DECISIONS (Operator, 2026-06-22) — surface FIRST
- **#197 Self-driving onboarding / autonomous DevOps agent** (Arad pilot feedback, verbatim in ticket + `tmp/arad-onboarding-feedback.md` + memory `ce-devops-onboarding-agent-differentiator`). 3 tiers: dialogue → computer-use autonomous DevOps → exact-steps fallback. Key differentiator (DevOps/infra setup is the un-automated market gap). Substrate = broker #185 + OpenBao #113 + install track.
- **#198 Dogfooding gap** — dev fleet runs from SOURCE (`python -m`), not installed `ce`; we don't dogfood the install/update lifecycle real users hit. Remedy = move fleet steady-state to installed `ce` + upgrade via publish(#80)/`ce update`(#190)/reinstall(#173) → raises W5 to P0. **DECISION PENDING: flip on source now (A, my rec) vs hold flip for installed-belt (B).** Awaiting Operator.

## ✅ #342 (#196 flip gate) MERGED — main at 2afc4801. Operator GO given on flip (source-now) + dogfooding migration (#198).
## 🚧 CANARY RAN (2026-06-22) — caught a NEW flip-blocker #200; FLIP HELD until fixed.
- One-item bounded canary on cedev2 (throwaway #199 / unique label, now cleaned up: forge claim wclaim-dea024b2 released, #199 closed, label deleted). Result: **#340 fix WORKS** (argv executes, no more "ce not found"); poll→claim WORKS; but **`lane launch` exits 1 → G3-CLAIM-MISSING**.
- **#200 = the blocker:** `pickup.launch_lane`/`build_lane_argv` (pickup.py:819/846) never allocate the **Active-Work lane claim** that `lane launch` hard-requires (`lane_runtime.py:748`, RV1-030, `claims/<id>/<lane>.yaml` under `.hermes/active-work-ledger`). `--enable-launch` self-describes as "S3 canary (default OFF)" — wired, never validated e2e. Flipping now = claim-and-fail every launch.
- Also learned: pickup poll includes **assigned** issues (not just --label) — it saw #176 assigned, correctly skipped (active_foreign_claim). A real flip poll claims assigned + labeled work.
- **My worker `adbc2c58` is building #200** (allocate claim+lease/pane before launch, reconcile ledger-root `.hermes/active-work-ledger` vs V3_LOCAL_STATE_ROOT, e2e test). On completion: I review→PR→merge→**re-run canary (must hit LAUNCHED_STATE + spawn a real lane)**→then flip seat crons (dev-1/dev-3; cedev2 stays read-only).

## NEXT-SESSION FIRST ACTIONS
1. Resolve #198 (flip on source vs installed). If A → `git -C ~/creator-engine pull` (done: 2afc4801) → run the one-item canary (python -m, claim form, scoped to one) → observe lane spawn → report → get GO → flip dev-1/2/3 crons.
2. Triage #343 (new self-picked PR) — route review to a non-author seat.
3. #337 (mine): confirm CI green post-rebase → nudge dev-4 re-approve → merge.
4. #335 (dev-4 #80) fix cycle → merge.
5. Fast-follow: #190 `ce update` (Release&Update epic #191, Arad canary ~Wed 24-Jun).
