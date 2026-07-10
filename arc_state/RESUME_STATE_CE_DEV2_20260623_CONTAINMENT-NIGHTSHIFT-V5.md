# RESUME STATE — CE-DEV-2 · 2026-06-23 ~17:30 UTC · 🏭 CONTAINMENT NIGHT-SHIFT v5 — 🎉 FIRST CONTAINED+HERDR CONTROLLER LIVE

**WHERE:** CE-DEV-2 controller, `cedev2` on DGX `spark-b824` (GB10 aarch64), cwd `/home/cedev2/creator-engine`, Opus 4.8 high. **SUPERSEDES** V4. **READ THIS + MEMORY.md FIRST.** Discipline: containment/runtime state PROBED via `ce containment-probe`, NEVER asserted ([[resume-state-claims-are-self-attestation]]).

## 🎉 MILESTONE ACHIEVED (PROBED 17:27 UTC) — dev-4 = first probe-verified, BORN-contained CE controller
Killed the wedged raw codex (no resume) → launched fresh contained+herdr from the clean home. LIVE + PROBED:
- **backend=gvisor, contained=true, gaps=[]** (`ce containment-probe` on the container's runsc-sandbox PID; runtime=runsc-gvproxy-ptrace).
- **herdr live**: codex (pid 46 in-container) running in herdr pane `w1:p1` (cwd /workspace/creator-engine); socket `/run/creator-engine/herdr/herdr.sock` = `srw------- uid 1002` (substrate-side, owner-only — seat cannot reach).
- **MODEL B verified**: contained codex env = `CLEAN_NO_TOKEN_NO_SOCKET` (no GH_TOKEN/GITHUB_TOKEN, no socket carrier). Zero creds in the box.

## ⏳ REMAINING to call dev-4 a *working* contained controller (next actions)
1. **DRIVABILITY** — the tmux pane `dev4stage1:0.0` shows herdr-SERVER stdout, NOT attached to the codex pane. Attach it: from the pane run `herdr` (the TUI client) / attach to workspace w1 pane w1:p1 so dev-4 is witnessable + steerable. (herdr told us: "run `herdr`; you do not need `herdr server`".)
2. **RE-ORIENT** — dev-4 came up FRESH (clean home has the born-a-foreman AGENTS.md). Give it a pointer to resume: its identity + this resume + its in-flight context (it had been building U-LAUNCHER #395 which MERGED; next herdr unit = U4 attribution shim).
3. **🔑 THE CRUX** — can the contained foreman SPAWN A WORKER inside the container (contained-by-inheritance, token-free)? THE existence proof for contained controllers. Verify a fan-out works from inside the box.
4. **B PUSH PATH** — confirm a dev-4 commit (in /workspace/creator-engine = bind-mounted host repo) lands host-side; the cedev2 controller pushes it (near-term B); dev-1's publish-gate is the durable enabler.

## 🛠️ CONTAINED dev-4 — EXACT MECHANICS (to re-probe/drive)
- Container: `docker ps --filter ancestor=creator-engine/codex-runsc:0.141.0-aarch64` (it's `docker run --rm`; CID rotates if relaunched — always re-find by ancestor).
- Clean home (host): `/home/cedev4/.codex-contained` (= ~/.codex minus the `[shell_environment_policy]` GH_TOKEN/GITHUB_TOKEN block). Foreman AGENTS.md preserved.
- LAUNCH (in tmux dev4stage1, TTY pane): `cd ~/ce-workspaces/creator-engine && CE_DGX_CODEX_HOME=/home/cedev4/.codex-contained CE_DGX_REPO=/home/cedev4/ce-workspaces/creator-engine ./deploy/dgx-runsc/run-codex-runsc.sh tui`
- PROBE (needs sudo + workspace cwd): `cd ~/ce-workspaces/creator-engine && PID=$(docker inspect $CID --format '{{.State.Pid}}') && sudo -n env PYTHONPATH=validators python3 -m creator_engine_validator.ce_cli containment-probe $PID --json`
- DGX sudo: cedev2 + cedev4 BOTH have passwordless sudo (Operator granted for the probe). VPS ce-pilot-1 too.
- Throwaway dry-run pattern: same launch with `exec "printf ok; sleep N"` + `CE_DGX_TTY_FLAGS=-i` backgrounded.

## 🎯 GOAL + remaining WAVE-2 (Operator, pre-dawn): contained FLEET + herdr, probe-verified
- ✅ DGX dev-4 contained+herdr (THIS milestone — finish validation per §⏳).
- ⏳ VPS seats (dev-1/dev-3 on ce-pilot-1): #396 = deploy/vps-runsc/ recipe. After it lands → relaunch dev-1+dev-3 contained (dev-3 derived the per-seat cmds; has sudo; probe each).
- ⏳ Controller (cedev2 = ME) LAST: the Claude-controller variant in #395; relaunches THIS session → behind a fresh probe-backed checkpoint.

## 🔴 BOARD
- **#398 gVisor-detect fix — MERGED** (main `35edfe5`; probe now reads backend=gvisor honestly; tightened to exact runsc-sandbox/gofer/runsc basenames, no `runsc*` glob).
- **#397 fleet-attestation (dev-1)** — fix pushed (Ring-1 probes through target proc-root; discovery derives from #392); HELD BEHIND main pending rebase onto #398 → then dev-3 final re-review.
- **#396 VPS contained+herdr (dev-3)** — fix pushed (env -i whitelist + real VPS probe); needs dev-1 (non-author) re-review. (dev-4 is the OTHER non-author but it's now contained/re-orienting.)
- **dev-1** — building the **substrate PUBLISH-GATE** (model-B enabler / the auditable chokepoint v1: host-side attributed FF-only push + side-effect-ledger record, reusing the Integrator push path). Fanning out.
- All earlier substrate PRs MERGED (#386-#395, #391/#392/#393/#394, #351).

## 📌 DECISIONS / MEMORY
- **Push model = B** (Operator-ratified, short+long term): contained seats COMMIT-only; substrate PUSHES host-side; ZERO creds in sandbox; long-term = broker-backed publish-service (OpenBao/SecretIdentityBackend). Framing: centralize cred into ONE auditable chokepoint. → memory [[ce-contained-controller-push-model]].
- Clean-build spec: `tmp/CLEANBUILD_SPEC_dev4_contained.md`. Codex-exec-break rescue lesson: memory [[codex-seat-exec-break-rescue]].
- ce-ops#222 egress confinement = staged follow-on (NOT tonight); egress_enforceable()->True is a false-attestation stub to fix.

## 🖥️ REACH
dev-4=`ssh cedev4@localhost -i ~/.ssh/id_ed25519` (tmux dev4stage1:0.0 — now the contained launch) · dev-3=`ssh dev3` (dev3-onboard:0.0) · dev-1=`ssh dev1` (ce-dev1-orchestrator:controller). overwatch gh: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Merge: the repo HAS a merge QUEUE — `gh pr merge <n> --auto` ENQUEUES (state stays OPEN til the queue runs validate on the merge commit; autoMergeRequest stays None — that's the queue, not a failure; just wait, do NOT assume stuck). Verify approval on CURRENT head (commit_id==headRefOid) before enqueue; dismiss stale CR only when a genuine independent approval already stands (#388/#351 precedent).
