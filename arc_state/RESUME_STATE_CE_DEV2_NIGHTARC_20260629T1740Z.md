# RESUME STATE — CE-DEV-2 Orchestrator — NIGHT-SHIFT ARC — 2026-06-29 ~17:40Z

> NEWEST. Open this + MEMORY.md FIRST. Night-arc = **balanced completion of all in-flight lanes + arming proof + automation-scaling work**, **FULL AUTONOMOUS** (standing G1–G5): drive/review/gate/merge through the night; surface only RESERVED items or hard blockers; checkpoint for morning. Author≠approver always.

> ✅ **RATIFIED by Operator — 2026-06-29 (this session).** Scope: balanced completion of ALL in-flight lanes (#652 canary, #358 installer-trust, Phase B support wiring, #353 Tranche-2) + arming proof + "massive automation-scaling work"; **full autonomous authority (G1–G5)** to drive/review/gate/merge through the night; surface RESERVED items + hard blockers only; checkpoint for the morning. This ratification IS the authority for the night-arc's autonomous gate/merge actions.

## AUTH
overwatch: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Approve as ce-dev-2: `GH_TOKEN=$(cat ~/.ce-keys/ce-dev-2.pat) gh pr review <n> --approve`. queue-daemon pid 43010 (wall+merge, logs `~/ce-wall-daemon.log`) auto-merges approved+green. Agent routing: reviewer/implementer/architect/harvest=sonnet, recon/triage=haiku, Opus=controller.

## 🟢 ARMING IS LIVE (ratified ce-ops#356, Operator "flip it" 2026-06-29)
- **Surface A (docs-class auto-merge):** repo Variables SET — `CE_AUTOMERGE_RUN_MODE=ceo` + `CE_AUTOMERGE_ENABLING_REF=https://github.com/creator-engine/ce-ops/issues/356`. Rollback: unset/`dev`. Blast radius docs-class only. NOTE: Decide reruns on push/reopen/merge_group (NOT on approval) — so an approved docs PR usually merges via the **daemon**; the pure CI path engages via merge_group. **CANARY PROVEN ✅ — #652 (docs-class) merged HANDS-FREE 2026-06-29T17:43:53Z, zero manual merge click.** Arming works on real PRs.
- **Surface B (autonomous APPROVE):** dev-3 review broker armed `CE_EGRESS_RUN_MODE=strangeLoop` (drop-in `/etc/systemd/system/ce-egress-self-review-dev3.service.d/run-mode.conf`). Rollback: `dev` + restart. Walls hold: author≠approver host-side + envelope. **Only dev-3's broker armed** — fleet-wide needs dev-4's broker pre-staged the same way (ce-ops#357 covers the broker-from-seat-checkout architecture fix first).

## 🔵 IN-FLIGHT SEATS (all Working as of 17:40Z)
- **dev-1** (non-contained VPS, self-push) → **ce-ops#358** installer trust fixes (uv manifest-pin hash-verify [security] + persist-verified-artifacts/fix printed next-step). MUST smoke-test install.sh end-to-end in a container before PR. Branch `ce-358-installer-trust-fixes`. (Redirected off a cron-fed #350 envelope brief it never started.)
- **dev-3** (contained ce-vps-codex) → **Support Phase B** (ce-ops#360): pluggable `CE_SUPPORT_AGENT_MODEL_CMD` model seam + per-answer NDJSON log (CLASS not raw text — PII) + tests vs a STUB model command (no live backend). Branch `ce-supportagent-phaseB-model-wiring`.
- **dev-4** (contained ce-dgx-codex, DGX) → **#353 Tranche-2** os-native sandbox EXECUTION (real bwrap+Landlock+seccomp+egress-proxy; cardinal: never run unsandboxed, fail-closed). Foreman correctly gating on "enforceable sandbox contract or no launch path." Branch `ce-353-tranche2-osnative-exec` (committed c211d44, validating). May land OR return a fail-closed blocker report — both acceptable.

## 🟣 BOARD / MERGES
- MERGED today incl **#651** (doctor packaging gate → `ce onboard` user-blocker FIXED) , #649/#650 (arming wiring + Mac runbook). **#652** (Mac runbook brain-init + version-drift fix) = **MERGED 17:43Z hands-free = Surface-A canary PROVEN.** Board empty as of 17:44Z.
- Review setup lesson: fetch `+<br>:refs/remotes/origin/<br>` + `git worktree add .ce/wt-ce<N>-review` BEFORE dispatching reviewer.

## 🟢 SUPPORT AGENT (ce ask) — pilot path
- Design = **ce-ops#360** (channel-agnostic core `support_runtime.answer_question()` → thin channel adapters → agency via `support_profile` extension; NanoClaw = Phase-F CONTAINMENT only, not the answering harness). Phases: A(P0 done)→B(wiring, dev-3 now)→C(Discord)→D(eval)→E(Slack)→F(external+NanoClaw)→G(actions+NemoClaw).
- **Backend = OpenRouter cheap-API for pilot** (key STORED `~/.ce-keys/openrouter.env` mode600; → move to OpenBao ce-kv at VPS deploy). Self-host vLLM = internal-tier backbone (DGX serves embeddings only today — generation endpoint not yet stood up). **Claude is BANNED** (Anthropic prohibits subscription-in-3rd-party-harness since 2026-04-04; SDK=per-token) — see [[ce-no-anthropic-sdk-per-token-billing]]. OpenAI-sub works via codex.
- After Phase B lands: wire OpenRouter backend → **zero-leak eval on real CE Q&A** (release-blocking) → `ce ask` answering for real. Budget cap ce-ops#355.

## 🟡 ONBOARDING (Nitzan = Mac; contributor)
- Path: Mac container runbook → `ce brain init` → `ce launch` (AVOID `ce onboard` until #359 fix proven). #651 merged the doctor fix → **re-verify F5** (`ce onboard` now works in a real user git repo) when a seat frees — closes the loop.
- #358 installer fixes (dev-1) harden the install path.

## 🎟️ TICKETS FILED THIS ARC
ce-ops#357 (broker→dedicated-checkout + fleet Surface-B pre-stage), #358 (installer uv-hash + dead-paths), #359 (ce onboard doctor blocker — FIXED via #651), #360 (support-agent design).

## 🟠 SCALING LANES QUEUE (dispatch as seats free — "massive automation scaling")
CEO-mode #291 (W1a, top bet) · forge autonomy/triage · fleet-wide Surface-B pre-stage (after ce-ops#357) · company-brain lanes · expand autonomous-merge confidence (carefully, gated). Probe territory + not-already-landed before dispatch.

## 👀 WATCHERS / HEARTBEAT
- Board Monitor **bh8s12igt** (ALIVE). Seat-READY Monitor **bxa44s2dn** (validate-edge; ALIVE). Hourly cron **0a34687f** (:47, session). System crons: seat-check :00, poll-devs :05, conveyor-tend :30.
- **GAP:** conveyor-tend auto-dispatch may NOT "take" (dev-1 was fed #350 but stayed idle). RELY ON hourly-cron me-verified restock (I confirm Working after every dispatch). Seat-IDLE isn't directly watched — hourly poll catches it.

## ON RESUME (fresh context)
1. Read this + MEMORY.md. 2. `gh pr list` + reconcile (#652 canary merged? dev-1 #358 PR? dev-3 Phase B READY? dev-4 Tranche-2 READY or blocker-report?). 3. Verify watchers (bh8s12igt, bxa44s2dn) + daemon (43010) + brain alive; re-arm if needed. 4. Harvest/review/gate any READY. 5. As seats free: F5 re-verify, wire OpenRouter backend + zero-leak eval, then scaling lanes (CEO-mode #291). 6. Keep all seats fed (verify Working); NO seat idle; NEVER inline. 7. Surface RESERVED/blockers; else drive autonomously.
