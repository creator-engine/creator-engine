# RESUME STATE — CE-DEV-2 · 2026-06-24 morning · 🏛️ THREE-DEPUTY GOVERNANCE ARCH + cred-mediation eval spike

**WHERE:** CE-DEV-2 controller, `cedev2` on DGX `spark-b824` (GB10 aarch64), cwd `/home/cedev2/creator-engine`, Opus 4.8 high. **SUPERSEDES V6** (V6 = full night-shift detail; read it for the build history). READ THIS + MEMORY.md FIRST. Discipline: containment PROBED via `ce containment-probe`, never asserted.

## 🔴 LIVE RIGHT NOW — pick up here
- **Eval spike DONE + committed** → `ce-ops/designs/RESEARCH_credmediation_eval_20260624.md` (ce-ops `7f5aa81`). Memory: [[ce-transport-deputy-tooling]]. **Recommendation = COMPOSITION (not one pick), Operator-ENDORSED onecli:** RENT **onecli** as the cred-injection gateway (Apache-2.0, inject-out/strip-back, git-over-HTTPS + GitHub-API, composes with gVisor+herdr; **Operator endorses it — corroborated: NanoClaw uses onecli in production, that's how Operator knows it**); REUSE **NemoClaw/OpenShell** deny-by-default egress *pattern* (not runtime; = pattern + NVIDIA pitch-alignment only); ADOPT **Microsoft ACS** (MIT) as the single policy schema driving BOTH PEPs (in-box hook + proxy); REJECT MXC runtime. **Key unlock:** CE's `gvisor_proxy_backend.py` already emits `EgressProxyConfig(deny_by_default=True)` + `network="proxy"` with the concrete proxy as an unfilled "deployment overlay" = **the onecli slot is already cut.** (Formal build-ratification still pending — endorsed ≠ ratified-to-build.)
- **2 open unknowns** (would change the call): (1) onecli's egress posture — is it default-deny for ALL traffic + native L7 method/path, or inject-only? (if inject-only, wrap w/ gVisor netns + ACS for L7). (2) onecli↔OpenBao (it ships Bitwarden, not Vault) + whether CE's `EgressProxyConfig` rule-shape drives it as-is or needs a shim. Both = a config spike.
- **⚠️ W5 finding (confirmed on main):** `run-controller-runsc.sh:180` AND `run-vps-runsc.sh:218` forward `CLAUDE_CODE_OAUTH_TOKEN` INTO the sandbox = a live credential-in-box. **Converting this controller (W5) naively leaks the OAuth token → W5 needs the Transport deputy (or a token-strip) FIRST.**
- **Watchers STOOD DOWN** (cron `133529ac` cancelled, Monitor `bxdk58yeh` stopped). No autonomous heartbeat. Do NOT re-arm unless asked.
- NOTE: my local DGX checkout `/home/cedev2/creator-engine` is on STALE branch `ce207-*` (pre-#396, lacks deploy/vps-runsc/). Probe/main work uses worktree `/home/cedev2/ce-main-probe` (origin/main). Consider syncing the main checkout.
- **Watchers are STOOD DOWN** (Operator is back + driving): cron `133529ac` CANCELLED, PR Monitor `bxdk58yeh` STOPPED. No autonomous heartbeat now — the night-shift loop is over. Do NOT re-arm unless asked.

## 🏛️ THE ACTIVE STRATEGIC THREAD — Three-Deputy governance model (captured, awaiting ratification)
Design doc: **`ce-ops/designs/DESIGN_THREE_DEPUTY_GOVERNANCE_20260624.md`** (committed 0d3847e). Memory: [[ce-three-deputy-governance-model]].
A cred-injection proxy stops key exfiltration but creates a **confused-deputy** problem. Defeat at 3 layers:
1. **Transport** (RENT — NemoClaw/onecli/OpenShell/MXC): cred-injection egress proxy (inject-out/strip-back) = ALSO the egress-confinement primitive (cred-injection + W6 egress = ONE layer). Evolves Model-B from commit-only → full mediated capability; **UNBLOCKS dev-1 conversion + the review-submission gap** [[ce-contained-seats-cannot-submit-reviews]].
2. **Authorization** (MODEL on Microsoft Entra): PDP/PEP split; JIT *ephemeral* per-session identity; endpoint allowlist; L7 per-op policy; attribution; **CAE** mid-session revocation → upgrades [[ce-autonomous-authority-doctrine]] static→dynamic. Invariant = durable-decision-before-act (= our #399 ledger-before-push). ONE policy source (`claims` artifacts) → both in-box hook AND proxy.
3. **Correctness** (BUILD — CE moat): authz tiers bound blast-radius but NOT intent (a scoped/attributed seat can still APPROVE bad code). Entra governs *access* + assumes human judgment sound; agents void that → grader-on-work/quorum/refusal-spine has no IAM analog = CE's irreducible core. Approval-that-gates-merge = privileged op → JIT-elevated independent approver, never blindly proxied.
**Stack:** rent transport · model authorization on Entra · build correctness. Pitch: *"Conditional Access + PIM for agent fleets, plus the correctness layer Entra was never built to have."*
**Operator has NOT formally ratified** the direction yet (engaged + steering it; said "kick off" the eval spike). Next gates: ratify direction → fork/rent decision (post-spike) → then the §8 open questions (single policy schema, PDP shape, CAE-for-agents signals, approval-quorum spec).

## ✅ NIGHT-SHIFT OUTCOME (done; detail in V6)
6 PRs merged to main: **#399** publish-gate (Model-B chokepoint v1) · **#396** VPS contained+herdr recipe · **#401** recipe trust+model fix · **#402** W6 egress fail-closed · **#403** VPS ops-notes · **#400** existence-proof doc. Milestones: **dev-4 (DGX) = first born-contained controller**; **dev-3 (VPS) = first contained VPS seat** (canary) — both exec + Model-B + probe-verified.

## 🖥️ FLEET STATE NOW (probe-verified this morning)
- **dev-4 (DGX)** = CONTAINED ✓ (gvisor, gaps=[]). Idle. Drive via herdr socket. CID rotates: `docker ps --filter ancestor=creator-engine/codex-runsc:0.141.0-aarch64 -q`.
- **dev-3 (VPS)** = CONTAINED ✓ (gvisor, gaps=['ns:net:host']=documented --network=host egress gap). Idle. `ssh dev3`; CID: `sudo docker ps --filter ancestor=creator-engine/codex-runsc:x86_64 -q`.
- **dev-1 (VPS)** = NON-contained — the credentialed reviewer (held deliberately; clean home pre-staged at /home/ce-dev-1/.codex-contained). `ssh dev1`, tmux pane `ce-dev1-orchestrator:2.0` (:0.0 DEAD).
- **cedev2 (me, DGX)** = NON-contained controller. W5 (convert me) = Operator-supervised, not done.
- **Board:** only **#397** open (fleet-attestation, rebased, review-BLOCKED by the contained-reviewer gap → resolved by Transport deputy). All else merged.

## 🛠️ MECHANICS (contained-seat drive)
- **Probe** needs a MAIN checkout (probe at ce_cli.py on main): worktree `/home/cedev2/ce-main-probe`. `PID=$(sudo -n docker inspect <CID> -f '{{.State.Pid}}'); sudo -n env PYTHONPATH=validators python3 -m creator_engine_validator.ce_cli containment-probe $PID --json`. (On VPS, run via `ssh dev3 "cd ~/creator-engine && ..."`.)
- **Drive contained codex** via herdr: `sudo docker exec -e HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock <CID> herdr pane read w1:p1 --source recent --lines N` · send: `herdr pane send-text w1:p1 "<msg>"` then `herdr pane send-keys w1:p1 Return`. ⚠️ **send-text messages must be plain ASCII — NO apostrophes or parens** (they break the ssh+docker+shell nesting). Key = **Return** (not Enter/C-m).
- **VPS conversion recipe lessons** (in tmp/VPS_CONVERSION_PLAN.md): seat user needs docker group (`usermod -aG docker`) + FRESH tmux server; generated config must pre-trust /workspace/creator-engine + set model (fixed in #401). Clean homes pre-staged on both VPS seats.
- **Model-B push** (host-side, contained seat's committed branch): `ssh devN 'cd ~/creator-engine && git push origin <branch>'` (host cred helper, never in box).
- overwatch gh: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Merge QUEUE: `gh pr merge <n> --auto` enqueues (state stays OPEN; isInMergeQueue=true; not stuck). Verify APPROVED on CURRENT head before enqueue.

## 📌 OPERATOR'S OPEN DECISIONS (morning queue, refined by the three-deputy model)
1. Ratify the three-deputy direction + (post-spike) the fork/rent candidate.
2. dev-1 VPS conversion — unblocks once Transport deputy lands.
3. W5 — convert THIS controller contained (supervised).
4. #397 review path (= the review-submission resolution).
