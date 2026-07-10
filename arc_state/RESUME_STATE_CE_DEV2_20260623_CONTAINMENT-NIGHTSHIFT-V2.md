# RESUME STATE — CE-DEV-2 · 2026-06-23 ~14:07 UTC · 🏭 CONTAINMENT NIGHT-SHIFT v2 (contained fleet + herdr)

**WHERE:** CE-DEV-2 controller, `cedev2` on DGX `spark-b824` (GB10 aarch64), cwd `/home/cedev2/creator-engine`, Opus 4.8 high. **SUPERSEDES** ...CONTAINMENT-NIGHTSHIFT.md (v1). **READ THIS + MEMORY.md FIRST.**

## ⚠️ DISCIPLINE — PROBED vs ASSERTED ([[resume-state-claims-are-self-attestation]])
A prior ce-dev2 resume chain falsely asserted "dev-4 CONTAINED gVisor" (never true, copied forward unprobed → reached Operator → INCIDENT). Containment/runtime state is **PROBED via `ce containment-probe`**, NEVER carried in prose. Mark every load-bearing claim PROBED (cite probe) or ASSERTED; re-probe each session; falsify dropped claims explicitly. The #392 matrix + #388 probe enforce this in code.

## 🎯 RATIFIED GOAL (Operator, end of night-shift / pre-dawn)
**Contained FLEET + herdr.** herdr REQUIRED for ≥ DGX controller tonight. Estimate as a controller driving N PARALLEL workers + MY OWN worker-spawn lane (Agent isolation:worktree → PR) ([[workload-estimation-controller-parallel]]) — decompose, dispatch ALL lanes at once, never serialize. Operator put me "in charge of the factory."

## 🟢 PROBED GROUND TRUTH
- **VPS `ce-pilot-1` (= CE-DEV-1 Hetzner, hosts BOTH ce-dev-1 uid1004 + ce-dev-3 uid1003) = CONTAINMENT SUBSTRATE PROVEN** (PROBED via my worker smoke test: `docker run --runtime=runsc-gvproxy-ptrace creator-engine/codex-runsc:x86_64` → `CONTAINED_OK`, kernel `4.19.0-gvisor`, uid=1004, egress OK). Docker 29.1.3 + containerd installed; runtimes `runsc`/`runsc-ptrace`/`runsc-gvproxy-ptrace` (all `--network=host`); image `creator-engine/codex-runsc:x86_64` (61.8MB, arch-neutral Dockerfile, no edits); `ce`/`cev3` 0.2.0 already on both seats' PATH. **Operator granted passwordless sudo** (sudoers.d/ce-dev-1, ce-dev-3; visudo OK). ⚠️ VPS uses `--network=host` → gVisor isolates kernel/fs/syscall but NOT network → egress allowlist is a follow-on (NOT contained on net yet).
- **DGX dev-4 working seat = RAW HOST, NOT contained** (PROBED forensics): raw `codex resume`, host namespaces, `/proc/root→/`. Contained recipe EXISTS (`deploy/dgx-runsc/run-codex-runsc.sh` + image `creator-engine/codex-runsc:0.141.0-aarch64`, runtime in /etc/docker/daemon.json) but bypassed.
- **codex Ring-1 = managed-non-bypassable** (PROBED via #392 from `.codex/requirements.toml` `allow_managed_hooks_only=true`; #387 MERGED). claude Ring-1 = full. **containment for ALL seats = deferred/unverified** (PROBED via #392 — herdr launch raises HerdrContainmentNotWired).
- **Isolation tier BUILT but UNWIRED into `ce launch`** (composition-root seam in progress = #389/#390/#391).

## 🔴 BOARD (gate: APPROVED on current head + green + CLEAN → `gh pr merge <n> --auto`)
- **#392** harness-matrix (#220, MY lane, ce-overwatch) — REVIEW_REQUIRED → route non-author + enqueue.
- **#391** compose gvisor runner into launch surfaces (dev-1, SUB-C seam integration) — UNSTABLE (CI) → dev-1 stabilize.
- **#390** backend selector (dev-1, SUB-A) — CHANGES_REQUESTED → dev-1 fix.
- **#389** docker-runsc render (dev-1, SUB-B) — CHANGES_REQUESTED (fail-closed: available() must verify runsc runtime registered; execute() must refuse unknown handle, no docker-exec fallback) → dev-1 fixing.
- **#388** containment-probe (#221 Fix-1, MY lane) — CHANGES_REQUESTED/BEHIND (only a docs-inventory sync: add `ce containment-probe` to inventory contract + manifest) → **dev-1 ON IT** (pane on ce221-containment-probe).
- **#386** Integrator runner (dev-1) — CHANGES_REQUESTED (atomic multi-file repair, no partial publish) → STILL NEEDS FIX (dev-1 jumped to seam; re-route).
- **#351** mint-broker — CHANGES_REQUESTED, parked.

## 🏭 FACTORY FLOOR (seats PROBED 14:07)
- **dev-1** (37% left, on #388 docs-fix): owns Integrator + composition-seam; fanned seam → #389/#390/#391. Queue: #388 docs-sync → #389/#390 fixes → #391 stabilize → #386 fix. FANS OUT workers.
- **dev-3** (70% left, on main, ~idle): did seam reviews. VPS now UNBLOCKED (sudo). Next: review #392/#391; then VPS CONVERSION (relaunch its own + dev-1's codex INTO the container).
- **dev-4** (80% left = recompacted, ⚠️ shows ce157-mint-broker branch — VERIFY it's actually on herdr-live ce217-u3live, may have drifted): SHOULD be building herdr-LIVE session API (wire HerdrSession send/observe against `~/herdr-ce/target/release/herdr` + register terminal_kind=herdr) → U4 (attribution shim) → U-LAUNCHER (herdr-ce inside gVisor container + controller variant). **RECHECK/re-dispatch herdr-live first thing.**
- **MY worker lane** (Agent isolation:worktree): delivered #388 (probe) + #392 (matrix) + VPS provision. FREE → reload (e.g. #388 docs-sync if dev-1 didn't finish, or controller-wrapper scaffold).

## 📋 NEXT ACTIONS (countdown)
1. **dev-4: RECHECK herdr-live status** (branch drift suspected) → re-dispatch if needed. Critical path for herdr.
2. Land seam: #389/#390 fixes → #391 stabilize → merge (= `ce launch --backend gvisor` real, fail-closed).
3. Route reviews: #392 (non-author), #391/#390/#389 re-reviews as fixed.
4. #388 docs-sync (dev-1) → merge (probe lands). #386 runner fix → re-route.
5. **VPS CONVERSION** (Wave 2): relaunch dev-1 + dev-3 codex INTO container via `run-codex-runsc.sh` with x86_64 env: `CE_DGX_IMAGE=creator-engine/codex-runsc:x86_64`, runtime `runsc-gvproxy-ptrace`, x86_64 codex bin/home, `CE_DGX_UID/GID`, `CE_DGX_CONTAINER_USER`. **Probe-verify each (`ce containment-probe`) before declaring contained.** At a CLEAN stop point per seat (don't kill in-flight work).
6. **DGX CONVERSION**: dev-4 contained+herdr (after U-LAUNCHER) → probe-verify → **controller (cedev2) LAST** (relaunches THIS session; behind a fresh probe-backed checkpoint).
7. Egress allowlist for VPS `--network=host` (follow-on; net not contained yet).
8. Dual-write this resume to CE-DEV-1 + ce-ops.

## 🎫 TICKETS
#218 Integrator runner→daemon · #219 codex Ring-1 (#387 MERGED ✅) · #220 harness SSOT (#392) · #221 containment PROBED + fail-closed launch (#388 Fix-1) · #128 whole-fleet→containment RATIFIED.

## 🖥️ MECHANICS / REACH
- dev-4=`ssh cedev4@localhost -i ~/.ssh/id_ed25519` (tmux `dev4stage1:0.0`, ~/ce-workspaces/creator-engine) · dev-3=`ssh dev3` (`dev3-onboard:0.0`) · dev-1=`ssh dev1` (`ce-dev1-orchestrator:controller`); dev-1/3 BOTH on ce-pilot-1 (Hetzner x86_64). codex gpt-5.5. Dispatch: `cat brief | ssh <h> "tmux load-buffer -b ce -; tmux paste-buffer -p -b ce -t <pane>; sleep 0.3; tmux send-keys -t <pane> Enter"`. Every brief leads w/ foreman preamble + FAN-OUT directive.
- overwatch gh: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. ce-ops sync: `cd ~/ce-ops && ./sync-ops.sh "msg"`.
- MY worker lane = Agent tool `isolation:worktree` → builds → PR → dev reviews. USE PROACTIVELY (don't leave idle — Operator directive).
- Peer review caught 3+ fail-closed bugs tonight (partial-publish, §7 socket-leak, runsc-availability) — model working; keep routing real verdicts.
