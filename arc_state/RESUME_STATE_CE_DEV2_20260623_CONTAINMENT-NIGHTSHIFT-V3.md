# RESUME STATE — CE-DEV-2 · 2026-06-23 ~15:15 UTC · 🏭 CONTAINMENT NIGHT-SHIFT v3 (contained fleet + herdr)

**WHERE:** CE-DEV-2 controller, `cedev2` on DGX `spark-b824` (GB10 aarch64), cwd `/home/cedev2/creator-engine`, Opus 4.8 high. **SUPERSEDES** ...NIGHTSHIFT-V2.md. **READ THIS + MEMORY.md FIRST.**

## ⚠️ DISCIPLINE — PROBED vs ASSERTED ([[resume-state-claims-are-self-attestation]])
Containment/runtime state is PROBED via `ce containment-probe` (now on main, #388), NEVER carried in prose. Same lesson now extends to EGRESS: `egress_enforceable()->True` is a false-attestation stub (ce-ops#222) — the SAME bug class as the dev-4 false-"contained" incident. NEVER assert a security property a probe hasn't confirmed.

## 🎯 RATIFIED GOAL (Operator, end of night-shift / pre-dawn)
**Contained FLEET + herdr.** herdr REQUIRED for ≥ DGX controller tonight. I am "in charge of the factory" — estimate as a controller driving N PARALLEL workers + MY OWN worker-spawn lane (Agent isolation:worktree → PR); decompose, dispatch ALL lanes at once, never serialize. REVIEWER seats ALSO fan out (Operator directive: dev-3 fans 3 review sub-workers like dev-1 fans 3 fixes).

## 🟢 PROBED GROUND TRUTH (15:15 UTC)
- **SEAM IS ON MAIN:** #386 integrator-runner · #387 codex Ring-1 (managed-non-bypassable) · #388 containment-probe (`ce containment-probe`) · #389 docker-runsc render · #390 backend-selector — ALL MERGED. `ce launch --backend gvisor` primitives now on main.
- **#393 herdr-LIVE = APPROVED+CLEAN+green → ENQUEUED** (HerdrSession.send/observe wired to real herdr binary; socket-ownership preserved — HERDR_SOCKET_PATH/HERDR_SOCKET refused from governed env; terminal_kind=herdr registered). THE long pole — landing.
- **VPS `ce-pilot-1` substrate PROVEN** (gVisor 4.19.0-gvisor smoke, sudo granted, image creator-engine/codex-runsc:x86_64). dev-3 derived per-seat relaunch cmds (dev-1: /home/ce-dev-1, uid1004; dev-3: /home/ce-dev-3, uid1003; both CE_DGX_IMAGE=...:x86_64, CE_DGX_RUNTIME=runsc-gvproxy-ptrace, CE_DGX_ALLOW_DOCKER_NETWORK=1).
- **herdr binary staged for dev-4 at /tmp/herdr-share** (aarch64, source+binary; src is `creator-engine/herdr-ce` master). Pane write contract: `herdr pane send-text|send-keys|run|read --source recent`.
- **EGRESS NOT confined on EITHER host** (gvproxy=NAT not allowlist; VPS=--network=host). Filed ce-ops#222 + design. STAGED follow-on, NOT tonight.

## 🔴 BOARD (gate: APPROVED on current head + green + CLEAN → `gh pr merge <n> --auto`)
- **#393** herdr-live — ENQUEUED ✅ (landing).
- **#394** contained-launch PROOF (dev-1, dev-1 e2e) — NONE/UNSTABLE — dev-1 rebasing onto main (was stacked on ce128-contained-launch-proof-base). Needs: clean rebase + green + non-author review.
- **#391** launch-runner integration SUB-C (dev-1) — REVIEW_REQUIRED/BLOCKED — I retargeted base→main; it's DIRTY (carries already-merged #389/#390 commits). dev-1 rebasing to drop dup commits, keep integration delta (compose-gvisor-runner+enforce-resolved-backend+stabilize-bridge), then needs fresh review.
- **#392** harness-matrix (MY lane) — REVIEW_REQUIRED/BLOCKED, but MERGEABLE+conflict-resolved (head 0a715ff8; merged main, unioned inventory keeping BOTH containment-probe+harness-matrix, 42 tests green). Just needs dev-3 RE-APPROVE on new head (mechanical merge-refresh; bundle w/ a quick nudge).
- **#351** mint-broker — CHANGES_REQUESTED, head f4081720 GREEN (dev-3's morning rate-cap fix). Both CRs are STALE (old head 6ad2e7ec). NO genuine approval on current head → CANNOT dismiss-enqueue. Needs a CLEAN reviewer = dev-1 or dev-4 (NOT dev-3, who authored the fix). Off critical path.

## 🏭 FACTORY FLOOR (PROBED 15:15)
- **dev-1** (⚠️ 18% — may auto-compact; RE-ENGAGE if it drops): stack cleanup — rebase #391 + #394 onto main (own stacked PRs; may force-push own branches). Then both need fresh non-author review.
- **dev-3** (43%): reviewing #393 (done, APPROVED). Queue: RE-APPROVE #392 (new head 0a715ff8, mechanical); + VPS dry-run (if not done). CANNOT review #351 (authored its fix).
- **dev-4** (33%): building **U-LAUNCHER** (herdr-ce inside gVisor container + Claude controller variant) = THE contained+herdr ship. After: U4 attribution shim. Branch display lags (shows ce157) — verify actual branch.
- **MY worker lane** (Agent isolation:worktree): delivered #388, #392, #392-manifest, #392-conflict, #351-attempt(stopped-correctly), egress-design(#222). FREE → reload (candidates: after #391 lands, the `egress_enforceable()` fail-closed micro-fix [collides with gvisor_proxy_backend while #391 rebases — HOLD]; or save egress design to ce-ops/designs).

## 📋 NEXT ACTIONS (countdown — DGX contained+herdr probe-verified)
1. **dev-1 @18% — watch for auto-compact**; re-engage onto stack cleanup if dropped. #391+#394 onto main → review → enqueue.
2. **#392 dev-3 re-approve** (mechanical) → enqueue. **#393** landing.
3. **U-LAUNCHER (dev-4)** = critical deliverable. When it lands → **WAVE 2 conversion**: relaunch dev-4 into [gVisor+herdr+codex+Ring-1] → `ce containment-probe` → contained:true → then **controller (cedev2) LAST** (relaunches THIS session via the Claude controller variant; behind a fresh probe-backed checkpoint).
4. #351 → route to dev-1/dev-4 (clean reviewer) when free.
5. VPS CONVERSION: relaunch dev-1+dev-3 codex into container (dev-3's derived cmds) → probe-verify each.
6. ce-ops#222 egress: stage the gh-aw-firewall fork + `egress_enforceable()` real probe (NOT tonight). Operator decision pending: model-API host set + key-in-sidecar.

## 🎫 TICKETS
#128 whole-fleet→containment · #216 integrator(#386✅) · #219 codex Ring-1(#387✅) · #220 harness SSOT(#392) · #221 containment PROBED(#388✅) · #217 herdr(#393 herdr-live) · **#222 egress confinement (NEW — false-attestation egress_enforceable)**.

## 🖥️ MECHANICS / REACH
- dev-4=`ssh cedev4@localhost -i ~/.ssh/id_ed25519` (tmux `dev4stage1:0.0`) · dev-3=`ssh dev3` (`dev3-onboard:0.0`) · dev-1=`ssh dev1` (`ce-dev1-orchestrator:controller`); dev-1/3 BOTH on ce-pilot-1 (x86_64). Dispatch: `cat brief | ssh <h> "tmux load-buffer -b ce -; tmux paste-buffer -p -b ce -t <pane>; sleep 0.4; tmux send-keys -t <pane> Enter"`. Every brief leads w/ foreman preamble + FAN-OUT directive (reviewers fan out too).
- overwatch gh: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Merge: `gh pr merge <n> --auto` (no --squash).
- Stacked-PR retarget that GraphQL-errors via `gh pr edit`: use REST `gh api -X PATCH repos/.../pulls/<n> -f base=main`.
- Dismiss stale CR ONLY when a genuine independent approval already stands on the current head (#388 precedent) — dismiss is NOT the approval.
