# RESUME STATE — CE-DEV-2 Controller (DGX) · 2026-06-19 PM (post day-shift batch)

**WRITTEN BY / WHERE:** the CE-DEV-2 controller running as **`cedev2` on the DGX `spark-b824`** (aarch64, tailnet 100.100.105.50), cwd `/home/cedev2/creator-engine`, Claude Opus 4.8 (effort high). Saved before an Operator context-clear. Read this FIRST, then `MEMORY.md`. **NEXT ACTION is in "▶ RESUME ENTRY POINT".**

## ⚠️ MODE CHANGE THIS SESSION (read before acting)
Operator **2026-06-19 RETIRED the dev-2 central-banking stopgap**. Each **dev-controller now self-pushes its OWN PRs as its own identity**; dev-2 (me) + Operator only **coordinate** (review/merge-gate) until the forge automates ticket-pick + autonomous tackling. dev-1/2/3/4 are **peer controllers**, NOT my worker-seats (the §7 push-block is on the *worker seats a controller spawns*, not on the controllers). Validated: dev-3 self-pushed #273 as `ce-dev-3`. (memory: [[ce-devs-are-controllers-not-seats]], supersedes [[ce-controller-owns-dev1-intake]].)

## SEAT → HOST → REACH (verify a handle resolves before acting)
- **dev-1** (codex controller, VPS) — **🟢 WORKING ce-ops#113 OpenBao go-live build**. `ssh ce@100.72.252.20` → tmux `ce-orchestrator:codex-ctrl`. Clone `/home/ce/creator-engine`. Self-pushes own PRs (cedev1vps identity).
- **dev-3** (codex controller, VPS) — **idle** (context-rotated after #133/#273). `ssh ce@100.72.252.20` → `sudo -n -u ce-dev-3 tmux ... -t dev3-onboard`. Clone `/home/ce-dev-3/creator-engine`. Self-pushes as `ce-dev-3` (provisioned, push works).
- **dev-4** (codex controller, CONTAINED gVisor, LOCAL DGX) — **idle**. `ssh cedev4@localhost` → tmux `dev4stage1`. **NEVER C-c.** Bundle from host `/home/cedev4/ce-workspaces/creator-engine` via `ssh cedev4@localhost`. aarch64 (only box that can verify aarch64).
- **Me** = cedev2 (DGX). Creds: `~/.ce-secrets/controller.env` (Max OAUTH — unset `CLAUDE_CODE_OAUTH_TOKEN` if it shadows `/remote-control`), `~/.ce-keys/ce-root-v1*` (signing), `~/.ce-keys/ce-forge-app.*` + `mint-forge-token.py` (`GH_TOKEN=$(python3 ~/.ce-keys/mint-forge-token.py)`). Independent review: `ssh ce@VPS "set -a; . ~/.ce-keys/reviewer.env; set +a; gh pr review <n> --approve ..."` as `cedev1vps-cmd` (distinct from authors).
- **py3.14 local verify:** `~/creator-engine/.venv` (uv-built, py3.14) reproduces CI — **verify green here before pushing** (test deps from PyPI; dev wheelhouse now dual-arch after #272). [[ce-dev2-dgx-py314-venv]]

## ▶ RESUME ENTRY POINT
1. **Re-arm the :08/:38 day-shift sweep cron** (CronCreate, session-only — gone after clear). Updated prompt: sweep 3 panes + open PRs; seats now SELF-PUSH so **coordinate review/merge, don't bundle**; handle signals; flag stalls/⏸️.
2. Verify reach to the 3 seats.
3. **Monitor two in-flight deliverables:**
   - **dev-1 → `DEV1 113-GOLIVE-PR`** (OpenBao go-live build). On its self-pushed PR: verify scope, CI green (pre-verify on .venv), independent review as cedev1vps-cmd, **coordinate merge**; then **surface the items-2/3 Operator bringup runbook to the Operator**.
   - **✅ Program plan DONE → PR #274** (`docs/v3.5-roadmap.md`, pushed as dev-2). **Awaiting Operator ratification** (+ a peer review; CI). On ratification → merge → it becomes the SoT replacing ad-hoc per-ticket triage. 7 workstreams (Containment / Team-mode PR throughput / Install-pilot / Secret&identity / Release-integrity / Docs&surface / Integrations), pitch + post-pitch-v4. **Post-ratification follow-ups in the PR:** put CRIT tickets in "Sept NVIDIA pitch" milestone + add `ws:*` labels; CLOSE stale-open cross-repo tickets (#94→#269, #126→#270, #134→#272, ce#237 dup, #85 via #88); FILE 2 docs tickets (README refresh, website/user-docs + dead `#docs` nav). Sanity-check soft placements: #92/#112, #73/#76, #74.

## BOARD — main HEAD = `facff85e`
**Shipped today (8 merges):** #269(#94+#127 forge-identity) · #270(#126 scope-target) · **#271 (v8 "Factory Floor" site — LIVE on creator-engine.dev)** · #272(#134 aarch64 dev wheels, #121 advanced) · #273(ADR-0006 accepted). **#88 closed** (plain-join DoD met via published-0.2.0 clean-room acceptance). v7 archived at `site-archive/index-v7-the-choice.html`.

## PENDING OPERATOR (⏸️)
- **ce-ops#113** items **2 & 3** (secret-zero injection; Shamir unseal + root-token custody — your trust-root acts, after dev-1's runbook lands) + **item-7 green-light** (live-secret migration, only after restore-drill #4 passes). Host LOCKED = Hetzner VPS, logically segregated (#113 comment).
- **v3.5-roadmap program plan** ratification (when fork's PR lands).
- **Close #133?** (ADR-0006 is now canonical tracker for its Gates 2-3) — Operator's call.
- **ce-ops#135** OpenBao dedicated micro-unit = scheduled fast-follow (not now).

## KEY GAPS surfaced today (folded into the program plan)
- **ce-ops#80 release process OPEN** — CE never formally released: SEMVER `0.2.0` but **ZERO GitHub tags/releases**. Couples with **#133 ADR-0006 Gate-2** (CI-built signed-release pipeline) → one Release-integrity workstream.
- **README** content stale (only incidentally touched). **Website/user docs**: the live v8 site's "Docs" nav is a **dead `#docs` anchor**; guide docs may be stale → Docs&surface workstream.

## MEMORY UPDATES THIS SESSION
Created: [[ce-dev2-dgx-py314-venv]], [[ce-devs-are-controllers-not-seats]]. Index: [[ce-controller-owns-dev1-intake]] marked RETIRED. Tickets opened: ce-ops#134 (done/merged), #135 (micro-unit). 
