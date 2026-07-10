# RESUME STATE — CE-DEV-2 · 2026-06-22 ~10:30 UTC · Autonomy gate MERGED; G8 flip pending #195 launch-argv + queue-hygiene

**WRITTEN BY/WHERE:** CE-DEV-2 controller as `cedev2` on the **DGX `spark-b824`** (dgx-spark-1/100.100.105.50, GB10, aarch64), cwd `/home/cedev2/creator-engine`, Opus 4.8 effort-high. SUPERSEDES `RESUME_STATE_CE_DEV2_20260622_AUTONOMY-BROKER-DRIVE.md`. **Read this + MEMORY.md first.** main ≈ `e963eaf4`.

## PEER-SEAT → HOST → REACH
- THIS host = DGX. dev-1 `ssh dev1` (tmux `ce-dev1-orchestrator` %0) · dev-3 `ssh dev3` (tmux `dev3-onboard` %2) [VPS, ce-dev-{1,3}] · dev-4 `ssh cedev4@localhost -i ~/.ssh/id_ed25519` (tmux %0) [DGX]. ⚠️ cedev2 (controller) does NOT have `ce`/`cev3` as executables — run the validator via `PYTHONPATH=validators .venv/bin/python -m creator_engine_validator[.ce_cli] …`. Seats (dev-1/3/4) HAVE `ce` on login PATH (NOT cron PATH — see #195).
- overwatch gh: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. ce-dev-2 PAT `~/.ce-keys/ce-dev-2.pat`. dev-4 self-pushes now (#175 fixed). Dispatch = short pointer+SHA (`tmux send-keys -t <pane> -l "..."; Enter; Enter`).
- ISSUE TRACKER = **creator-engine/ce-ops** (private). CODE/PRs = **creator-engine/creator-engine**.

## 🎯 AUTONOMY (arc ce-ops#186 W2) — GATE MERGED, FLIP PENDING
- **#338 (#194 planner hygiene) MERGED** → on main. **Mechanism VALIDATED via live canary on #176:** poll ✓ · claim+collision-guard ✓ · self-contained seed written ✓ · `build_lane_argv` ✓ · #194 correctly excludes open-PR in-flight (#173/#135/#113 dropped) ✓.
- **TWO flip-blockers the canary caught (NOT yet fixed):**
  1. **#195** — `launch_lane` shells bare `ce lane launch`; `ce` not in cron (non-login) PATH → `--enable-launch` silently no-ops fleet-wide. FIX = `build_lane_argv` uses `[sys.executable,"-m","creator_engine_validator.ce_cli","lane","launch",…]`. **dev-3 BUILDING** (brief `~/dev3-195-launch-argv.txt` sha 18399b31, branch ce195-launch-argv-python-m).
  2. **Queue-hygiene completeness** — planner excludes open-PR in-flight but NOT done-but-still-open / held / meta (a ce-ops issue stays OPEN after its PR merges → looks ready). Manually cleaned the belt queue to **[132,137,141,162,176]** (genuinely-ready). Needs a #194-followup so unsupervised re-runs stay clean.
- **FLIP PATH (resume here):** #195 merges → **re-run the one-item launch canary on dev-4** (codex + `ce` present; `ssh cedev4` … `ce pickup poll --identity ce-dev-4 --repo creator-engine/ce-ops --label ce-pickup/triage-ready --claim --enable-launch --harness codex --seed-root ~/ce-belt/seeds --repo-root ~/ce-workspaces/creator-engine --lane-ledger-root ~/ce-belt/lanes` scoped to ONE item) → confirm a governed lane spawns → **flip dev-1/3/4 belt crons to `--claim --enable-launch`** (with login PATH; NOT the cedev2 controller). Then queue-hygiene-completeness fast-follow.
- Belt read-only poll crons still live on dev-1/2/3 (5-min). Claim release syntax: `ce claim release <n> --repo … --claim-id wclaim-… --reason …`.

## OPEN PRs (creator-engine)
- **#339** (dev-3) ce-ops#192 CI shallow-fetch retry fix — REVIEW → dev-1.
- **#337** (me, ce-overwatch) ce-ops#151 stale-review reconciler — green after fixes (classified forge.re_review in v3 taxonomy + bumped V3_RUNTIME count 48→49); re-review → dev-4. Conservative auto-dismiss rule: dismiss a CR only when its commit≠head AND a DIFFERENT reviewer approved head.
- **#335** (dev-4) ce-ops#80 signed-publish — CHANGES_REQUESTED, dev-4 fixing.
- **#334** (dev-1) ce-ops#173 idempotent reinstall — CHANGES_REQUESTED, dev-1 fixing.
- **#333** (dev-3) ce-ops#185 broker Slice-1 — CHANGES_REQUESTED, dev-3 fixing.
- (#195 PR pending from dev-3.)

## MERGED TODAY: #322 #309 #323(ADR-0011) #327(G6 enforce) #329(#187 triage) #331(G9) #332(OpenBao ADR-0012) #338(#194 hygiene).
## TICKETS FILED TODAY: #184(pinned broker-1st-envelope) #185 #186(arc) #187 #188(reviews-pickup: belt-half done in pickup.py, gap=#151) #189(courier supersession-guard) #190(ce update) #191(Release&Update epic) #192(CI flake→#339) #193(nanoclaw study) #194(triage hygiene→#338 merged) #195(launch-argv). CLOSED done: #157 #153 (+ earlier #175 push-cred).

## RELEASE & UPDATE TRACK (epic #191, pre-Arad-canary gate; Arad onboarding ~Wed 24-Jun, floats to gate-green)
- #173 idempotent reinstall (#334, fixing) · #80 signed publish (#335, fixing) · #190 `ce update` CLI (NOT started) · #192 CI flake (#339). Web-UI update button = fast-follow (ADR-0008 web UI on main, not built). Canary must run a live `ce update` cycle as acceptance.

## HELD CHECKPOINTS (await Operator release): OpenBao deploy (#113/#135) · install-sig (#158) · first DevOps-broker envelope EXECUTION (#184 VPS /tmp tmpfs = the pinned inaugural task).

## OTHER STATE
- DevOps broker (#185): ADR-0011 merged; Slice-1 (#333) in review-fix; #184 = first envelope (held).
- W4 OpenBao: ADR-0012 + LocalSecretIdentityBackend merged (#332); #137/#147 identity NOT started.
- Memories written today: `ce-verify-not-superseded-before-courier`, `ce-belt-nanoclaw-spawn-per-task-convergence`, `sakana-fugu-orchestration-research`; updated `ce-dev4-dgx-spark-access` (push-cred FIXED).
- ⚠️ Reviewer/seat-idle gap persists: every push→re-review→merge hop needs a controller nudge until the belt flip + #151/#188 land. Controller still = review-router + merge-gate.
- DGX-local zombie panes (cockpit/egress/website/webui) KILLED — board clean; only %0 (me) + %77 (root escape-hatch, unused).

## NEXT-SESSION FIRST ACTIONS
1. Check #195 (dev-3) → review+merge → run dev-4 launch canary → **flip dev-1/3/4 = autonomy LIVE.**
2. Drive the fix-cycle PRs to merge (#333/#334/#335/#337/#339) — nudge re-reviews (idle gap).
3. Queue-hygiene-completeness #194-followup (detect merged-PR-done + held) for safe auto-re-runs.
4. #190 `ce update` CLI (Release&Update gate for Arad canary).
