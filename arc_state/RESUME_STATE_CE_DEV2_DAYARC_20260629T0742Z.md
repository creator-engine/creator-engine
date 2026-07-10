# RESUME STATE — CE-DEV-2 Orchestrator — DAY-SHIFT ARC — 2026-06-29 ~07:42Z — checkpoint for fresh-context continuation

> NEWEST. Operator asked to checkpoint + continue with fresh context. Open this + MEMORY.md FIRST. Supersedes the 0513Z checkpoint.
> ⭐ ROLE: OVERARCHING ORCHESTRATOR — drive via seats/workers, NEVER inline. Author≠approver. AUTONOMOUS=dispatch/harvest/review/gate/merge; RESERVED→HALT (arming FLIPS, release-sign, deploy, fleet-rollout, history-scrub).

## AUTH
overwatch: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Approve as ce-dev-2: `GH_TOKEN=$(cat ~/.ce-keys/ce-dev-2.pat) gh pr review <n> --approve`. queue-daemon (pid 43010) auto-merges approved+green. Agent routing pinned (reviewer/implementer/architect=sonnet, verification/recon=haiku, Opus=controller).

## 🟢 BIG PICTURE — this session drove the ARMING-COMPLETION lane + ONBOARDING
The night-arc built the arming MACHINERY but it was never wired to a live trigger. This session verified that end-to-end and is WIRING the real arming path (all INERT until the Operator sets a knob). Plus support-agent + Mac onboarding for the first user (Nitzan) + contributor.

## 🔴 TOP THREAD #1 — ARMING COMPLETION (ce-ops#356) — both surfaces, building the real wiring
"Arm it" approved BOTH surfaces; the FLIP stays reserved. The checkpoint-claimed "edit policy.json" was a NO-OP (gitignored, absent in CI) — verified. Real state:
- **Surface A (auto-merge):** runs as ephemeral GitHub Actions CI (Decide workflow → on-completion Actuate workflow → actuator CLI enables GitHub native auto-merge). NO daemon. Blast radius = docs-class only (docs/**, *.md, changelogs, manifests).
  - Gap 1 (live kill_switch re-verify) ✅ MERGED #645.
  - Gap 2 (CI materialization) + Gap 3 (decision artifact stamps repo/branch/base) → **dev-4 building** branch `ce-armA-arming-wiring` (was rebasing onto fresh main, ~commit 1643067; LAST arming piece). On READY → harvest→review→gate.
  - (Gap: required_checks already = ["Validate governance artifacts"] — fine.)
- **Surface B (autonomous APPROVE):** a PERSISTENT per-seat daemon (egress self-review broker, e.g. pid 88895 on VPS = `ce-egress-self-review-dev3.service`). ✅ run-mode wiring MERGED #647.
- **THE REAL ARMING KNOBS (present as consolidated one-tap once dev-4's Surface A merges):**
  - Surface A: set GitHub Actions **repo Variable `CE_AUTOMERGE_RUN_MODE=ceo`** (+ `CE_AUTOMERGE_ENABLING_REF`=ratification record). Rollback: unset/dev. (Exact knob name pending dev-4's impl — VERIFY against the merged wiring.)
  - Surface B: set **`CE_EGRESS_RUN_MODE=strangeLoop`** in the broker EnvironmentFile (`%h/.config/creator-engine/ce-egress-self-review.env`) + **restart** the per-seat self-review broker(s). Rollback: dev + restart.
  - BOTH reserved. Walls hold regardless: author≠approver (host-side, unspoofable) + envelope; auto-merge blast radius = docs-class only.

## 🔵 TOP THREAD #2 — SUPPORT AGENT (`ce ask`) — FUNCTIONAL; bot build awaiting greenlight
- `ce ask` answering path **MERGED #644** (cite-or-refuse fail-closed, zero-leak, dev-gated, offline-safe tests). Corpus WIDENED #646 (contributing-to-ce + playbook docs scrubbed→product-lens, re-added to allowlist).
- DECISIONS LOCKED: (a) internal-infra corpus = DEFER (pilot on product-lens); (b) Discord = two servers, START with one external; (c) **model backend = OpenRouter cheap-API for pilot — NOT Anthropic SDK (standing constraint [[ce-no-anthropic-sdk-per-token-billing]]); self-hosted DGX only forced for the DEFERRED internal tier.** Budget cap = ce-ops#355 (~$30/mo default, fail-closed).
- ⏸️ **AWAITING OPERATOR: greenlight the bot build.** Scope = one external product-lens Discord bot on the VPS (Python + discord.py, minimal harness, OpenRouter backend, support_profile read-only gate) → zero-leak eval → internal tier later. dev-1 is the likely seat (idle now).

## 🟣 ONBOARDING (first user Nitzan = Mac; contributor)
- **Mac via Linux container** (Docker Desktop + existing Linux wheels) = onboard TODAY, no Darwin build. Native-Mac port (#352) DEFERRED. Mac-via-container runbook → **dev-3 building** branch `ce-mac-container-onboarding` (product-lens, grounded in install.sh). NOTE: needs an end-to-end smoke test before handing to Nitzan.
- **#353 os-native selectability fix** (governed escape-hatch, fail-closed) → **#648 APPROVED + gated by ce-dev-2 → MERGING** (cardinal no-unsandboxed-path invariant verified; run() refuses execution; scoped to selectability+probe+scaffold — full bwrap+Landlock execution = Tranche-2 follow-on; 2 probe-hardening notes recorded on ce-ops#353).

## 🟢 RATIFIED THIS SESSION
- **OQ-1 = Option A** (bwrap+Landlock+seccomp+egress-proxy; macOS Seatbelt parallel; gvisor DEFAULT; os-native user-elected fail-closed; CE-native jail deferred). Recorded on ce-ops#353/#352. CONSISTENT with OpenShell/NemoClaw (different axes — see corrected model below).
- Arming BOTH surfaces (build the wiring; flip reserved).

## CORRECTED MODEL (Operator) — do NOT re-conflate
- **OpenShell** = NVIDIA zero-trust **sandbox-orchestration RUNTIME** (gateway control-plane + sandbox/supervisor enforcement; sandboxes via Docker/Podman/VM or k8s pods). The isolation layer — SAME axis as CE gvisor/os-native.
- **NemoClaw** = open-source **reference blueprint / lifecycle / onboarding wrapper** that installs OpenShell + operates agents inside it. NOT a harness.
- **Harness** (codex/Claude/OpenClaw/Hermes) runs INSIDE the OpenShell sandbox.
- CE FIT: on the NVIDIA platform CE **delegates** isolation to OpenShell (no own gVisor — double-jail); standalone CE = os-native(OQ-1)/gvisor. OQ-1 governs the standalone path; OpenShell the on-platform path → not competing. [[openshell-nemoclaw-stack]]

## IN-FLIGHT SEATS
- **dev-4** (contained ce-dgx-codex, DGX) → Surface A wiring `ce-armA-arming-wiring` (Gap 2/3). LAST arming piece. Was rebasing onto fresh main.
- **dev-3** (contained ce-vps-codex, VPS) → Mac-via-container runbook `ce-mac-container-onboarding`.
- **dev-1** (non-contained VPS, self-push) → IDLE (just pushed #648). Next = support-bot build (on greenlight) or next lane.

## BOARD / MERGE TALLY (this session-arc)
MERGED: #641 ARM-B, #642 ARM-A, #643 OQ-1, #644 ce-ask, #645 kill_switch, #646 corpus-scrub, #647 Surface-B. **#648** (#353 os-native) APPROVED+gated → MERGING. dev-4 Surface A PR + dev-3 Mac doc PR incoming. queue-daemon ALIVE; brain UP (vLLM Qwen3 :8989).

## WATCHERS (re-arm if session changed)
- Board Monitor **bh8s12igt** (queue-churn filtered) — ALIVE. Seat-READY Monitor **bxa44s2dn** (dev-3/dev-4 contained) — ALIVE. Hourly cron **0a34687f** (:47). (A duplicate cron 2963feea was deleted; my own board monitor bfmzgsfsk was stopped as redundant.)

## TICKETS FILED THIS SESSION
ce-ops#355 (support-agent cost/budget cap — gates prod/hosted exposure), #356 (arming completion — both surfaces).

## MEMORIES WRITTEN THIS SESSION
ce-fetch-worktree-before-reviewer-dispatch · ce-no-anthropic-sdk-per-token-billing · ce-deployment-tiers-solo-vs-team · ce-mac-onboarding-via-linux-container.

## LESSONS LOCKED THIS SESSION
- **Set up the review worktree BEFORE dispatching a reviewer** (reviewer is read-only, can't fetch): `git fetch origin <br>:refs/remotes/origin/<br>` (use `+` to force-fetch a force-pushed branch) → `git worktree add .ce/wt-ce<N>-review origin/<br>` → point reviewer at it. Else false "branch not accessible" REQUEST_CHANGES. [[ce-fetch-worktree-before-reviewer-dispatch]]
- **Contained-seat file delivery:** docker cp does NOT reach the bwrap'd seat; use `docker exec -i ce-dgx-codex bash -lc "cat > /var/tmp/<file>"` (shared mount). NOT /tmp (PrivateTmp) or /workspace (perm-denied). VPS seats via `ssh dev1 'sudo docker exec -i ce-vps-codex ...'`. dev-1 (non-contained) → `ssh dev1 'cat > ~/ce-briefs/...'`.
- **herdr dispatch:** file-based pointer `herdr agent send w1:p1 "$(cat /var/tmp/ptr.txt)"` then `herdr pane send-keys w1:p1 Enter`; verify the **Working** indicator (the pane STATUS BAR shows a stale cwd/branch — confirm via Working + the worktree commit, not the status bar). dev-1 = tmux `send-keys -t ce-dev1-orchestrator:2.0 -l "$(cat /tmp/ptr.txt)"` + Enter.
- **In-container validate watcher** must `docker exec pgrep` INSIDE the container, not host; require N consecutive confirmed-empty polls (a single transient docker-exec failure false-fires "finished").
- **Self-fire heuristic:** when the harvest worker commits a code fix (authored ce-overwatch), the reviewer flags self-fire → returns COMMENT not APPROVE; controller gates as ce-dev-2 (≠ author) — substance still valid. Prefer the author seat make code fixes, not the harvest worker.
- Seats correctly self-refuse out-of-scope (dev-4 rebased before declaring READY; dev-3 stopped on a RED test outside its allowed paths → re-briefed with the test file added).

## ⏸️ CONSOLIDATED AWAITING-OPERATOR QUEUE (surface FIRST on resume)
1. **Arming one-tap** (both surfaces) — compose + present the moment dev-4's Surface A wiring MERGES; exact knobs above + rollback. RESERVED.
2. **Support-agent bot build greenlight** — backend settled (OpenRouter cheap-API pilot); awaiting "go" to scope the build handoff.

## ON RESUME (fresh context)
1. Read this + MEMORY.md. 2. `gh pr list` + reconcile: #648 merged? dev-4 Surface A PR landed? dev-3 Mac doc PR? 3. Verify watchers (bh8s12igt, bxa44s2dn) + queue-daemon (43010) alive; re-arm if needed. 4. Harvest/review/gate any READY (dev-4 Surface A = then the arming one-tap; dev-3 Mac doc; #648). 5. Surface the ⏸️ AWAITING-OPERATOR queue (arming one-tap once Surface A in main; support-bot greenlight). 6. dev-1 idle → support-bot build on greenlight, else next probed lane. Keep the conveyor fed; NO seat idle; NEVER inline.
