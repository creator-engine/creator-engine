# RESUME STATE — CE-DEV-2 · 2026-06-23 ~15:35 UTC · 🏭 CONTAINMENT NIGHT-SHIFT v4 (contained fleet + herdr)

**WHERE:** CE-DEV-2 controller, `cedev2` on DGX `spark-b824` (GB10 aarch64), cwd `/home/cedev2/creator-engine`, Opus 4.8 high. **SUPERSEDES** V3. **READ THIS + MEMORY.md FIRST.** Probe, don't assert ([[resume-state-claims-are-self-attestation]]); egress_enforceable()->True is a false-attestation stub (ce-ops#222), same bug class as the dev-4 false-contained incident.

## 🎯 GOAL (Operator, pre-dawn): Contained FLEET + herdr, PROBE-verified. I'm "in charge of the factory" — N parallel worker lanes incl my own; reviewers fan out too; never serialize.

## 🟢 PROBED GROUND TRUTH (15:35) — SUBSTRATE FULLY ON MAIN
MERGED: #386 integrator · #387 codex Ring-1 · #388 containment-probe (`ce containment-probe`) · #389 docker-runsc · #390 backend-selector · #391 launch-runner integration (SUB-C) · #392 harness-matrix SSOT · **#393 herdr-LIVE** (HerdrSession.send/observe on real binary; terminal_kind=herdr; socket-ownership enforced). `ce launch --backend gvisor` + herdr session API are LIVE on main.
- VPS `ce-pilot-1` substrate PROVEN (gVisor smoke, sudo granted, image creator-engine/codex-runsc:x86_64). dev-3 derived per-seat relaunch cmds.
- herdr binary staged for dev-4 at /tmp/herdr-share (aarch64). Pane write: `herdr pane send-text|send-keys|run|read --source recent`.

## 🔴 BOARD — the contained+herdr SHIP funnels to #395
- **#395 U-LAUNCHER (dev-4)** = THE keystone, dev-4 FIXING 2 real findings (dry-run did its job — caught NO-GO before live conversion):
  - **FIX B (glibc NO-GO):** host-built herdr needs GLIBC_2.39 but image=bookworm/glibc2.36 → herdr never starts. FIX = BUILD herdr-ce from source in a Dockerfile builder stage on the bookworm base (stop smuggling the host binary). **This same fix unblocks BOTH the DGX AND the VPS x86_64 contained+herdr images.**
  - **FIX A (dev-3 §7 leak):** harness still inherits CE_DGX_HERDR_SOCKET_PATH; entrypoint scrubs only raw HERDR_SOCKET_PATH/HERDR_SOCKET via `env -u`. FIX = scrub CE_DGX_-prefixed socket carrier too + regression test (no socket name under ANY env prefix).
  - Then RE-DRY-RUN + `ce containment-probe` → contained:true before re-review.
- **#394 contained-launch PROOF — MERGED ✅** (on main). **#393 herdr-live, #391/#392 — MERGED ✅.**
- **#351 mint-broker — ENQUEUED** (dev-1 INDEPENDENT approval + dev-3 both on current head f4081720; landing). Off critical path.

## 🏭 FACTORY FLOOR (15:50) — all lanes on distinct contained-FLEET fronts
- **dev-4**: #395 U-LAUNCHER FIXES (glibc-from-source + CE_DGX socket-scrub + RE-DRY-RUN). DGX front. Critical path.
- **dev-3** (fresh, auto-compacted ~96%): **VPS contained+herdr** track — new `deploy/vps-runsc/` x86_64 recipe (herdr-FROM-SOURCE + CE_DGX socket-scrub baked in from #395's lessons) + launcher + dry-run+probe on ce-pilot-1. Fanning out 3 workers. → VPS contained+herdr PR.
- **dev-1** (fresh, auto-compacted ~82%): **Fleet containment ATTESTATION** track — `ce containment-status` probing EVERY seat {contained,backend,herdr,ring1} fail-closed (extends #388+#392). Fanning out 3 workers. → fleet-probe PR. The tool that proves WAVE 2 BY PROBE.
- **MY worker lane** (Agent isolation:worktree): delivered #388/#392/#392-conflict/#351-attempt(stopped-correctly)/egress-design(#222). FREE — held for the WAVE-2 conversion + gate. My own context ~15% → checkpoint+/clear imminent.

## 📋 NEXT ACTIONS (WAVE 2 — the conversion, imminent)
1. **dev-4 dry-run probe** = go/no-go. If contained:true + herdr-live + socket-boundary holds → proceed.
2. Enqueue **#394** (re-approved) + **#395** (approved) → U-LAUNCHER lands on main.
3. **WAVE 2 CONVERSION** (gated, I drive): relaunch dev-4 into [gVisor+herdr+codex+Ring-1] via run-codex-runsc.sh (the #395 path) → `ce containment-probe` confirm contained:true → **then VPS** (relaunch dev-1+dev-3 via dev-3's derived cmds, probe each) → **controller (cedev2) LAST** (Claude-controller variant; relaunches THIS session — behind a fresh probe-backed checkpoint).
4. #351 → enqueue once dev-1's independent approval lands (clears stale CR).
5. ce-ops#222 egress (NOT tonight): fork gh-aw-firewall + egress_enforceable() real probe. Operator decision pending: model-API host set + key-in-sidecar.

## 🎫 #128 fleet-containment · #217 herdr (#393✅ live; #395 U-LAUNCHER; U4 next) · #216(#386✅) #219(#387✅) #220(#392✅) #221(#388✅) · #222 egress (NEW).

## 🖥️ MECHANICS
- dev-4=`ssh cedev4@localhost -i ~/.ssh/id_ed25519` (dev4stage1:0.0) · dev-3=`ssh dev3` (dev3-onboard:0.0) · dev-1=`ssh dev1` (ce-dev1-orchestrator:controller); dev-1/3 on ce-pilot-1 x86_64. Dispatch: `cat brief | ssh <h> "tmux load-buffer -b ce -; tmux paste-buffer -p -b ce -t <pane>; sleep 0.4; tmux send-keys -t <pane> Enter"`.
- overwatch gh: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Merge `gh pr merge <n> --auto`. Stacked retarget if GraphQL-errors: REST `gh api -X PATCH .../pulls/<n> -f base=main`. Dismiss stale CR ONLY when a genuine independent approval stands on current head (#388 precedent).
- Verify approval is on CURRENT head before enqueue: compare review commit_id vs headRefOid.
