# RESUME STATE — CE-DEV-2 Orchestrator — NIGHT-SHIFT ARC — 2026-06-29 ~18:16Z

> NEWEST. Open this + MEMORY.md FIRST. Supersedes 1740Z. Night-arc = **balanced completion of all in-flight lanes + arming proof + automation-scaling work**, **FULL AUTONOMOUS** (standing G1–G5, Operator-ratified this session): drive/review/gate/merge through the night; surface only RESERVED items or hard blockers; checkpoint for morning. Author≠approver always.

## AUTH
overwatch: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Approve as ce-dev-2: `GH_TOKEN=$(cat ~/.ce-keys/ce-dev-2.pat) gh pr review <n> --approve`. queue-daemon pid 43010 (wall+merge, logs `~/ce-wall-daemon.log`) auto-merges approved+green. Routing: reviewer/implementer/architect/harvest=sonnet, recon/triage/verification=haiku, Opus=controller.

## 🟢 ARMING LIVE + PROVEN (ratified ce-ops#356)
- Surface A docs-class auto-merge: repo Vars `CE_AUTOMERGE_RUN_MODE=ceo` + `CE_AUTOMERGE_ENABLING_REF=…/ce-ops/issues/356`. Rollback unset/`dev`. **Canary #652 merged HANDS-FREE 17:43:53Z ✅.**
- Surface B autonomous-APPROVE: ONLY dev-3 broker armed (`CE_EGRESS_RUN_MODE=strangeLoop` drop-in). Fleet-wide pre-stage = ce-ops#357 (dev-4 part-1 building the decouple NOW; part-2 run-mode drop-in deferred to me until part-1 lands).

## 🔵 IN-FLIGHT SEATS (all Working as of 18:16Z) — extraction = git bundle out of container, NOT push
- **dev-1** (non-contained VPS, self-push) → **ce-ops#358** installer trust (uv manifest-pin hash-verify [security] + dead next-step paths). MUST container-smoke install.sh before PR. Branch `ce-358-installer-trust-fixes`.
- **dev-3** (contained ce-vps-codex, VPS) → **zero-leak EVAL harness** (ce-ops#360, release-blocking): NEW FILES ONLY (support_eval.py + fixtures + tests vs STUB model), do NOT edit support_runtime.py. Branch `ce-supportagent-zeroleak-eval`. Brief `/var/tmp/ce-briefs/ce-360-zeroleak-eval-dev3.md`.
- **dev-4** (contained ce-dgx-codex, DGX) → **ce-ops#357 part-1** broker-decouple (run broker from stable checkout, not seat tree; unit template + governed update script + tests; do NOT deploy). Branch `ce-357-broker-decouple`. Brief `/var/tmp/ce-briefs/ce-357-broker-decouple-dev4.md`. Just freed from Tranche-2 (now PR #653).

## 🟣 BOARD / HARVEST PIPELINE
- **#653** OPEN, REVIEW_REQUIRED = **Tranche-2** (dev-4) os-native sandbox exec probe+provision, **fail-closed by design** (never run unsandboxed; refuses w/o enforceable contract). Harvested GREEN (16 gates, 5882 tests, env-only seat failures = container libsodium gap, did NOT reproduce on host). Review worktree `.ce/wt-ce653-review`. **Reviewer ae1efdba running** → on APPROVE, approve as ce-dev-2 → daemon merges. It is a code-class PR (not docs) → normal gate.
- **Phase B harvest (a7acdd51) IN FLIGHT** → will open a PR `feat(support): Phase B model-backend wiring…` (ce-ops#360). On PR: fetch+worktree+reviewer (independent venue), then gate.
- MERGED today: #651 (doctor fix → ce onboard user-blocker FIXED), #652 (canary), #645–650.

## 🟢 SUPPORT AGENT (ce ask) pilot path
Phase A (P0, #644) done → **Phase B harvesting now** → next: wire backend (OpenRouter key STORED `~/.ce-keys/openrouter.env` mode600) + zero-leak eval (dev-3 building harness now) → ce ask answering. Claude BANNED (no Anthropic SDK/sub-in-3rd-party). Backend rec: OpenRouter cheap-API pilot / self-host vLLM backbone (DGX serves embeddings only today). Phases C(Discord)/D(eval)/E(Slack)/F(NanoClaw containment)/G(actions) later as adapters/extensions.

## 🟡 ONBOARDING (Nitzan = Mac, today)
- **F5 RE-VERIFIED PASS** (haiku, post-#651): `ce onboard` no longer blocks on RED-G-6 in a user repo; RED-G-6 still fires correctly in CE source tree. Path for Nitzan: Mac container runbook → `ce brain init` → `ce launch` (avoid bare `ce onboard` edge).
- **CAVEAT to watch**: in a BARE user repo (offline) `ce onboard` refuses **RED-G-4 (ungoverned state-path)** until `.hermes/` exists+gitignored. Likely an offline artifact (online install phase may provision it) — NOT confirmed as a real blocker. Verify online-onboard flow before handoff; possible fast-follow if it's an opaque papercut.

## 🩺 INFRA (verified this resume)
- **Brain `vllm-qwen3-embed` was DOWN** (died 17:47Z post-checkpoint) → **RESTARTED, serving** Qwen3-Embedding-8B :8989. Watch for repeat death.
- Daemon pid 43010 ALIVE (healthy passes). Crons: seat-check :00, poll-devs :05, conveyor-tend :30, hourly 0a34687f :47.
- **Watchers RE-ARMED** (died w/ /clear): board `b9aipnn3b`, seat-transition `bs2rmjt2y`. (Old session monitors bh8s12igt/bxa44s2dn also still firing — redundant, harmless.)
- Harvest extraction recipe: contained seat `git bundle create /var/tmp/harvest-out/<x>.bundle <merge-base>..<branch>` (thin) → `docker exec … cat` (NOT docker cp — /workspace RO, /tmp unreachable) → host `~/ce-harvest/`. dev-3 via `ssh dev1`. herdr dispatch: write pointer to in-container file, `herdr agent send w1:p1 "$(cat /var/tmp/ce-ptr.txt)"` + send-keys Enter (avoids cross-shell quoting of `(`).

## 🟠 SCALING QUEUE (note: CEO-mode #291 is CLOSED — its policy IS the live arming)
forge autonomy/triage (needs design pass) · fleet-wide Surface-B (ce-ops#357 in flight) · company-brain lanes · expand auto-merge confidence (gated). Probe territory + not-already-landed before dispatch.

## ON RESUME
1. Read this + MEMORY. 2. `gh pr list` reconcile (#653 merged? Phase B PR up? new seat branches?). 3. Verify watchers + daemon(43010) + **brain :8989** (re-died?). 4. Harvest/review/gate READY. 5. Keep seats fed (verify Working, NEVER inline). 6. After Phase B merges: wire OpenRouter backend. After #357 part-1 lands: do part-2 broker run-mode drop-in on dev-4. 7. Surface RESERVED/blockers; else drive.
