# RESUME STATE — CE-DEV-2 · 2026-06-23 (~13:30 UTC) · 🏭 CONTAINMENT NIGHT-SHIFT (contained fleet + herdr)

**WRITTEN BY/WHERE:** CE-DEV-2 controller as `cedev2` on DGX `spark-b824` (GB10 aarch64), cwd `/home/cedev2/creator-engine`, Opus 4.8 effort-high. **SUPERSEDES** RESUME_STATE_CE_DEV2_20260623_HERDR-COCKPIT-AND-AUTONOMY.md. **READ THIS + MEMORY.md FIRST.**

## ⚠️ PROBED-vs-ASSERTED DISCIPLINE (this session's hard lesson — [[resume-state-claims-are-self-attestation]])
Containment / runtime state is **PROBED**, never carried in prose. A prior ce-dev2 resume chain falsely asserted "dev-4 CONTAINED gVisor" (never true, copied forward unprobed → reached Operator → incident). NEVER repeat. Mark every load-bearing claim PROBED (cite probe) or ASSERTED; re-probe each session; falsify dropped claims explicitly.

## 🎯 RATIFIED GOAL (Operator, by end of night-shift / pre-dawn)
**Contained FLEET + herdr.** DGX (dev-4 + controller) contained + herdr + Codex Ring-1 TONIGHT (herdr REQUIRED for ≥ DGX controller); VPS (dev-1/dev-3) + canonical seam by dawn. Operator put me "in charge of the factory" → estimate as a controller driving N PARALLEL workers + MY OWN worker-spawn lane ([[workload-estimation-controller-parallel]]); decompose, dispatch ALL lanes at once, never serialize behind seats freeing.

## 🔴 PROBED GROUND TRUTH (containment)
- **dev-4 working seat = RAW HOST, NOT contained** (PROBED via forensics 2026-06-23): pid 179574 raw `codex resume`, namespaces identical to host shell, `/proc/179574/root→/`, host user-slice cgroup. The "contained" belief was false self-attestation in the prior resume chain. The contained recipe EXISTS + works on DGX (`deploy/dgx-runsc/run-codex-runsc.sh` + image `creator-engine/codex-runsc:0.141.0-aarch64`, runtime `runsc-gvproxy-ptrace` in /etc/docker/daemon.json) but the live seat bypassed it (raw `exec codex`).
- **gVisor/runsc IS live on the DGX** (Docker/containerd runtime=runsc) — runtime present; gap is CE not launching seats into it.
- **Isolation tier BUILT but UNWIRED:** RunnerBackend (gvisor_proxy/openshell) registered, `lane_runtime`/`launch_runtime` spawn straight through the VISIBILITY backend (tmux); `--backend` flag is a banner label only. herdr-in-container blocked on same orphaned seam. ASSERTED (from code-read worker, origin/main).
- **VPS (dev-1/dev-3) x86_64:** NO docker daemon, containerd inactive, ce not installed, aarch64 image won't run there. ASSERTED (probed hosts).

## 🏭 FACTORY FLOOR (lanes, all parallel)
- **dev-4** (DGX foreman): #387 codex Ring-1 managed-only fix → herdr U4 (attribution shim) → **U-LAUNCHER** (extend run-codex-runsc.sh: herdr-ce INSIDE the gVisor container + controller/Claude variant). OWNS deploy/dgx-runsc + herdr.
- **dev-1** (VPS foreman): #386 runner fix → **composition-root seam** (fan out 2-3 workers: `--backend` selector ∥ docker-runsc render in gvisor_proxy_backend ∥ lane_runtime thread ∥ runtime-policy ∥ herdr-U2-live).
- **dev-3** (VPS foreman, ⚠️ 11% ctx → RESET first): reset → self-provision its VPS host (docker+containerd+runsc + rebuild x86_64 image + install ce).
- **MY worker lane** (cedev2 Agent/worktree): U-PROBE #221 DONE (#388). Use for more parallel units.

## 🔴 BOARD (gate: reviewDecision==APPROVED on current head + green + CLEAN → `gh pr merge <n> --auto`; queue handles BEHIND)
- **#388** containment-probe (#221 Fix-1, MY worker, author ce-overwatch) — REVIEW_REQUIRED → route non-author (any dev) + enqueue. The verify-don't-trust guard.
- **#387** Codex Ring-1 hook-pack (dev-4) — CHANGES_REQUESTED → dev-4 fixing (pin `allow_managed_hooks_only=true` fail-closed).
- **#386** Integrator runner (dev-1) — CHANGES_REQUESTED → dev-1 fixing (atomic multi-file repair, no partial publish).
- **#351** mint-broker — CHANGES_REQUESTED, parked (needs fix, route when seat free).
- MERGED today (24 PRs): incl herdr U1/U2/U3 (#378/#379/#384), Integrator U1-U4 (#374/#375/#380/#383), #163 req-1/2/3 (#376/#381/#382), Codex Ring-1 base, forge.re_review Phase-2 (#385), #349 live-site.

## 🎫 TICKETS (this session)
#218 Integrator runner belt-poller→daemon · #219 Codex Ring-1 (native PreToolUse hook VIABLE — Operator was right, worker wrong; #387 builds it) · #220 harness-support SSOT (probed matrix) · #221 containment PROBED-not-reported + fail-closed launch (#388=Fix-1) · #128 whole-fleet→containment RATIFIED.

## 📋 NEXT ACTIONS
1. Route #388 review (non-author dev) → enqueue (incident guard).
2. dev-4: #387 fix → U4 → U-LAUNCHER. dev-1: #386 fix → seam (fan out). dev-3: reset → VPS provision.
3. **CONVERSION** (gate/me, Wave 2): relaunch dev-4 into contained+herdr → **`ce containment-probe` says contained:true** → then controller conversion LAST (relaunches THIS session; behind a fresh probe-backed checkpoint so contained-me resumes).
4. Strip GH_TOKEN injection from codex config + scoped no-push creds (U-CRED, fold into U-LAUNCHER).
5. Pre-existing flake to ticket: `tests/unit/test_ce_check_cli.py::test_ce_check_wraps_validator_check_json` fails on clean main (unrelated).
6. Dual-write this resume to CE-DEV-1 + ce-ops.

## 🖥️ MECHANICS / REACH
- dev-4=`ssh cedev4@localhost -i ~/.ssh/id_ed25519` (tmux `dev4stage1:0.0`, ~/ce-workspaces/creator-engine) · dev-3=`ssh dev3` (`dev3-onboard:0.0`, ~/creator-engine) · dev-1=`ssh dev1` (`ce-dev1-orchestrator:controller`, ~/creator-engine). codex gpt-5.5. Dispatch: `cat brief | ssh <h> "tmux load-buffer -b ce -; tmux paste-buffer -p -b ce -t <pane>; sleep 0.3; tmux send-keys -t <pane> Enter"`. **Every brief leads with foreman preamble.**
- overwatch gh: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. ce-ops sync: `cd ~/ce-ops && ./sync-ops.sh "msg"`.
- My own worker lane = Agent tool isolation:worktree → PR → dev reviews. Used for U-PROBE (#388); use proactively for parallel units.
