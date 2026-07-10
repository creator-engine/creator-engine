# RESUME STATE — CE-DEV-2 · 2026-06-23 ~18:30 UTC · 🌙 CONTAINMENT NIGHT-SHIFT v6 — FLEET CLOSURE ARC (RATIFIED, IN MOTION)

**WHERE:** CE-DEV-2 controller, `cedev2` on DGX `spark-b824` (GB10 aarch64), cwd `/home/cedev2/creator-engine`, Opus 4.8 high. **SUPERSEDES V5.** READ THIS + MEMORY.md FIRST. Discipline: containment PROBED via `ce containment-probe`, NEVER asserted.

## ☀️ MORNING HANDOFF (Operator returns) — read this first
**Night delivered (all merged to main):** #399 publish-gate (Model-B chokepoint v1) · #396 VPS contained+herdr recipe · #401 recipe trust+model fix · #402 egress attestation fail-closed (W6). Plus #403 VPS ops-notes doc (in review). **dev-3 = first contained VPS seat** (gVisor+herdr, exec, Model-B all probe-verified) — recipe proven end-to-end.
**Fleet containment state NOW:** dev-4 (DGX)=CONTAINED ✓ · dev-3 (VPS)=CONTAINED ✓ · dev-1 (VPS)=NON-contained (credentialed reviewer) · cedev2/me (DGX controller)=NON-contained.
**YOUR MORNING DECISIONS / blocked items (all need you):**
1. **🔑 Review-submission chokepoint** — THE blocker: contained seats can't SUBMIT PR reviews (zero creds to fetch diff/post). Review analog of Model-B; needs a host-side attributed submit path ([[ce-contained-seats-cannot-submit-reviews]]). Until it exists, can't contain the LAST credentialed seat without stranding peer-review.
2. **dev-1 VPS conversion** — deferred (kept as reviewer per #1). Recipe ready (fixed main + clean home pre-staged at /home/ce-dev-1/.codex-contained). Convert once #1 decided.
3. **W5 — convert THIS controller (cedev2) contained** — your supervised call.
4. **#397 fleet-attestation** rebased but review-blocked by #1; **#400 proof PR** minor (stale check + needs rebase).
**Automation still armed:** hourly heartbeat (dev-care+compact) + PR Monitor. Night log: tmp/nightshift_log.md.

## ✅ MILESTONE COMPLETE — dev-4 = first born-contained CE controller, FULLY validated (all 5 axes)
1. Contained (probe: backend=gvisor, contained=true, gaps=[]). 2. Drivable (herdr socket). 3. Oriented.
4. **Exec works** — fixed the nested-bwrap blocker: `sandbox_mode="danger-full-access"` in the clean home (codex's inner bwrap can't nest in gVisor; gVisor IS the sandbox; +approval_policy=never = YOLO, Operator-required, safe-because-contained). [[ce-contained-codex-needs-yolo-gvisor-is-sandbox]]
5. **Worker-spawn + Model-B** proven: contained foreman spawned token-free worker (PID 701, TOKEN=NONE) → in-box commit `8759939` (ce-dev-4, zero creds) → pushed host-side via host cred helper → origin. Proof artifact = **PR #400** (branch ce-contained-controller-proof).

## 🛠️ CONTAINED dev-4 MECHANICS (CID ROTATES on relaunch — always re-find)
- Find: `docker ps --filter ancestor=creator-engine/codex-runsc:0.141.0-aarch64 --format '{{.ID}}'` (now 815decb59dba).
- Clean home (host): `/home/cedev4/.codex-contained` — NOW has sandbox_mode=danger-full-access (.bak-presandboxfix kept).
- Launch (in tmux dev4stage1:0.0): `cd ~/ce-workspaces/creator-engine && CE_DGX_CODEX_HOME=/home/cedev4/.codex-contained CE_DGX_REPO=/home/cedev4/ce-workspaces/creator-engine ./deploy/dgx-runsc/run-codex-runsc.sh tui`
- **PROBE** (needs a MAIN checkout — probe is at ce_cli.py on main; my stale branch lacks it): worktree at `/home/cedev2/ce-main-probe` (origin/main). `cd /home/cedev2/ce-main-probe && PID=$(sudo -n docker inspect $CID --format '{{.State.Pid}}') && sudo -n env PYTHONPATH=validators python3 -m creator_engine_validator.ce_cli containment-probe $PID --json`
- **DRIVE/READ dev-4** (herdr over the in-container socket): `sudo -n docker exec -e HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock $CID herdr pane read w1:p1 --source recent --lines 40` · send: `herdr pane send-text w1:p1 "<msg>"` then `herdr pane send-keys w1:p1 Return` (key is **Return**, NOT Enter/C-m). Codex pane = w1:p1.
- **OPERATOR WATCH cmd**: on DGX, `CID=$(docker ps --filter ancestor=creator-engine/codex-runsc:0.141.0-aarch64 -q|head -1); sudo docker exec -it -e HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock $CID herdr` (interactive TUI; keystrokes reach codex).

## 🎯 ARC v6 — RATIFIED (Operator 2026-06-23 eve). Run autonomous to the merge GATE. Spec: tmp/NIGHTSHIFT_ARC_v6_containment_fleet_closure.md
- **W2 VPS contained** (dev-1+dev-3 on ce-pilot-1; they HAVE passwordless sudo there): land #396 (recipe + sandbox fix) → I drive their contained relaunch (born-clean, strip GH_TOKEN env, set danger-full-access) → probe + exec + worker-spawn + Model-B each.
- **W3 publish-gate**: land #399 → route a contained seat's push THROUGH the gate (attributed/FF-only/ledger).
- **W4 attestation**: rebase+land #397 → run `ce containment-status` fleet-wide (honest false for unconverted).
- **W6 egress honesty**: fix egress_enforceable()->True false stub (ce-ops#222); confine or honestly attest --network=host.
- **W5 controller-last conversion = ⛔ DEFERRED to MORNING arc, Operator-SUPERVISED. DO NOT run tonight.**
- Grants 1-5 GRANTED (convert VPS devs / merge #396,#397,#399 when APPROVED+CLEAN+green / Model-B push / open+merge egress fix / author-dispatch units, hold gate myself). Proof PR #400 = land it.

## 🔴 BOARD + DISPATCH (in flight)
- **#396** VPS recipe (dev-3, br ce128-vps-contained-herdr, head b613f33) — dev-3 ADDING sandbox fix (danger-full-access) + in-box exec acceptance; THEN dev-1 re-reviews combined head → merge → unblocks VPS conversion. (Was CHANGES_REQUESTED by dev-1 16:27.)
- **#399** publish-gate (dev-1, br ce-contained-publish-gate) — dev-1 FIXING dev-3's blocking finding: push happens BEFORE ledger record (publish_gate.py:342/356) → write intent record BEFORE push, fail-closed. THEN dev-3 re-reviews.
- **#397** fleet attestation (dev-1, br ce222-fleet-containment-attestation) — CONFLICTING/DIRTY; dev-1 REBASING onto main (#398 merged) → dev-3 final review.
- **#400** proof PR (open, ce-dev-4 commit) — needs a non-author review (dev-1/dev-3 when free); low priority.
- ⚠️ dev-1 pane ce-dev1-orchestrator:**0.0 is DEAD**; live codex is **:2.0** (dispatch there). dev-3 = dev3-onboard:0.0. dev-4 = contained (drive via herdr socket, above).
- ⚠️ VPS /tmp is a 16G tmpfs **100% full** (stale ce-pr* review dirs) — stage briefs to ~ not /tmp; told dev-3 to clean.

## 🖥️ REACH / MECHANICS
dev-1=`ssh dev1` (ce-dev1-orchestrator:2.0) · dev-3=`ssh dev3` (dev3-onboard:0.0) · dev-4=contained (herdr socket). overwatch gh: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Merge QUEUE: `gh pr merge <n> --auto` ENQUEUES (state stays OPEN until queue runs validate on merge commit; not stuck). Verify APPROVED on CURRENT head before enqueue.

## 🎉 PROGRESS (as of ~20:45 UTC)
- **#399 publish-gate MERGED** (W3.1). **#396 VPS recipe MERGED**.
- **🎉 dev-3 = first contained VPS seat (CANARY PROVEN)**: gVisor+herdr, probe backend=gvisor/contained=true (gaps=[ns:net:host]=documented --network=host egress gap), exec works, gpt-5.5/high, Model-B proven (in-box commit b8ff6ff→pushed→PR #401). Container rotates; find via `sudo docker ps --filter ancestor=creator-engine/codex-runsc:x86_64`. Drive via herdr socket like dev-4 (socket /run/creator-engine/herdr/herdr.sock, pane w1:p1). Probe: `ssh dev3 "cd ~/creator-engine && SBX=\$(sudo docker inspect -f '{{.State.Pid}}' <CID>) && sudo env PYTHONPATH=validators python3 -m creator_engine_validator.ce_cli containment-probe \$SBX --json"`.
- **2 recipe gaps fixed** (see VPS_CONVERSION_PLAN.md header): docker-group for seat user + fresh tmux server; generated-config trust+model (PR #401, dev-3-authored, in dev-1 review).
- **⚠️ FINDING — contained seats can't submit reviews** ([[ce-contained-seats-cannot-submit-reviews]]): review analog of Model-B; needs a review-submission chokepoint. → **dev-1 conversion DEFERRED to supervised morning** (keep it credentialed reviewer; don't strand review capacity). #397 review pending (morning item).
- IN FLIGHT: contained dev-3→W6 (ce222-egress-honesty, commit-only); dev-1→review #401+#400.

## 🤖 AUTOMATION ARMED (Operator signed out ~18:45 UTC; autonomous till morning)
- **Hourly heartbeat cron** `133529ac` (:17 each hour, session-only): dev-care + /compact each seat (dev-1/dev-3 via tmux, dev-4 via herdr socket) + arc-drive + logs to tmp/nightshift_log.md. dev-4 = SPECIAL (probe contained + drive/compact via herdr, relaunch if container gone).
- **PR Monitor** `bxdk58yeh` (persistent): wakes me on any PR → APPROVED/CLEAN or MERGED, so enqueue + the #396→VPS-conversion fire promptly between beats.
- **VPS conversion = execution-ready**: tmp/VPS_CONVERSION_PLAN.md (recon-verified; both VPS homes ALREADY clean+danger-full-access; image+runtime present; codex bin = npm-vendored musl ELF; launcher deploy/vps-runsc/run-vps-runsc.sh w/ CE_VPS_*; gated on #396 reachable — dev-3 has the branch, dev-1 needs the recipe). I (cedev2) drive each relaunch.
- **W6 egress** (#222): gvisor_proxy_backend.py:203 egress_enforceable()->True false stub; PARALLEL-SAFE w/ #397 (disjoint files). Dispatchable now.
- **Night log**: tmp/nightshift_log.md (append one line per beat/event).

## ⚡ POSTURE: NO THROTTLING (Operator 2026-06-23 eve)
DRIVE the current GPT Pro x20 toward 0% — a SECOND GPT Pro x20 account exists; Operator switches to it in the morning for a fresh weekly pool. Run seats as FULL FOREMEN (fan out 3-4 parallel worker lanes each, don't serialize). Controller (me) also spawns its own worker lanes (Agent tool) for prep/recon/review rather than inlining. Claude Max x20 weekly renews ~23:20 UTC (4h52m from 18:30) — ample for a controller + 3-4 lanes. STOP gating sub-codex spawns. Push the arc hard. (Full autonomy end-state = forge triage + autonomous agentic belt so each seat self-picks tickets & drives 3-4 lanes — NOT there yet; controller still stocks queues.)
