# RESUME STATE — CE-DEV-2 Orchestrator — NIGHT-SHIFT ARC — 2026-06-29 ~19:10Z

> NEWEST. Supersedes 1848Z. Open this + MEMORY.md FIRST. Night-arc = balanced completion of all in-flight lanes + arming proof + automation-scaling, **FULL AUTONOMOUS** (standing G1–G5, Operator-ratified): drive/review/gate/merge; surface only RESERVED/hard-blockers; checkpoint for morning. Author≠approver always.

## AUTH
overwatch: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Approve as ce-dev-2: `GH_TOKEN=$(cat ~/.ce-keys/ce-dev-2.pat) gh pr review <n> --approve`. queue-daemon pid 43010 auto-merges approved+green. Routing: reviewer/harvest/implementer/architect=sonnet, recon/triage/verification=haiku, Opus=controller.

## 🟣 BOARD = EMPTY (all merged). MERGED this session: #651 (onboard RED-G-6 unblock), #652 (canary, hands-free), #654 (installer uv trust), #653 (Tranche-2 os-native exec scaffold, fail-closed), #655 (onboard RED-G-4 guidance), #656 (Phase B support model wiring). origin/main = 1b1fbab0.

## 🔵 SEATS (all Working as of 19:10Z) — extract = git bundle out of container (NOT push); herdr/tmux pointer+sha
- **dev-1** (non-contained VPS, self-push) → **OpenRouter model-command adapter** (ce-ops#360 backend): NEW standalone artifact matching `CE_SUPPORT_AGENT_MODEL_CMD` JSON-over-stdin→stdout contract, fail-closed, live-smoke + mocked CI test. Branch `ce-support-openrouter-adapter`. Brief `~/ce-briefs/ce-360-openrouter-adapter-dev1.md`.
- **dev-3** (contained ce-vps-codex) → **Phase C Discord adapter** (ce-ops#360): thin channel adapter over `answer_question()`, discord client INJECTED behind a seam (no hard discord.py dep, no live net), mock-tested. NEW FILES ONLY. Branch `ce-supportagent-discord-adapter`. Brief `/var/tmp/ce-briefs/ce-360-discord-adapter-dev3.md`. (Just freed from zero-leak eval → PR harvesting, worker a2f51dd3.)
- **dev-4** (contained ce-dgx-codex) → **ce-ops#357 part-1** broker-decouple (stable checkout not seat tree). Branch `ce-357-broker-decouple`. (Part-2 = dev-4 broker run-mode drop-in = MY ops, after part-1 lands.)

## 🟢 SUPPORT PILOT — core wiring LANDED, backend next
P0(#644) + **Phase B model seam (#656) now IN MAIN**. Remaining to go live:
1. **dev-1 OpenRouter adapter** PR → review+gate+merge → then **WIRE** `CE_SUPPORT_AGENT_MODEL_CMD` to point at the adapter (key `~/.ce-keys/openrouter.env`; pick a cheap OpenRouter model) — THIS is the controller wiring step that lights up `ce ask`.
2. **dev-3 zero-leak eval** PR (harvest a2f51dd3 in flight) → review+gate+merge → RUN it against the wired backend = release-blocking eval on real CE Q&A.
3. dev-3 **Discord adapter** (building) → Phase C channel (Operator wants Discord today). Live Discord token+gateway+deploy = controller/deploy step later.
Contract: JSON(SupportRequest.to_dict()) on stdin → answer on stdout, exit0; non-zero/timeout→refusal. Claude BANNED as backend.

## 🟡 ONBOARDING (Nitzan, today) — path FIXED in main
#651 (RED-G-6 unblock, F5-verified) + #655 (RED-G-4 actionable guidance, reviewer-verified correct) + #654 (installer trust) ALL MERGED. Remaining: a FULL container e2e verify (fresh container → install one-liner → `ce brain init` → `ce onboard` → `ce launch`) — route to **dev-1** when it frees (it has container+network capability; contained seats + no-egress verifier can't do a live install). Then mark handoff-ready + fix any residual welcome.md/runbook drift.

## 🩺 INFRA
- Brain `vllm-qwen3-embed` :8989 RESTORED this resume (died 17:47Z) — serving. Watch repeat death.
- Daemon 43010 ALIVE. Crons seat-check:00 poll-devs:05 conveyor-tend:30 hourly:47. Watchers board b9aipnn3b+bh8s12igt, seat bs2rmjt2y+bxa44s2dn.
- HARVEST GOTCHAS [[ce-harvest-carrier-slug-must-match-branch]]: (1) carrier stem MUST==branch_slug(pushed head) or CI path-manifest gate fails closed (local validate-pr misses it); (2) `carrier_gen.write_carriers` OMITS the work-class line — re-add manually. Extract recipe: thin bundle `<merge-base>..<branch>` → `docker exec cat` out (NOT docker cp) → host `~/ce-harvest/`. dev-3 via ssh dev1. herdr dispatch: write pointer to in-container file then `herdr agent send w1:p1 "$(cat …)"` + send-keys Enter.

## 🟠 SCALING (CEO-mode #291 CLOSED — its policy IS the live arming)
forge autonomy/triage (needs design pass) · fleet-wide Surface-B = ce-ops#357 (dev-4 part-1) · company-brain · expand auto-merge (gated). Tickets filed this session: ce-ops#357/358/359/360/361.

## ON RESUME
1. Read this + MEMORY. 2. `gh pr list` reconcile (adapter/eval/#357/discord PRs up? merged?). 3. Verify watchers + daemon 43010 + brain :8989. 4. Review+gate any PR (independent venue; approve as ce-dev-2). 5. **When dev-1 adapter merges → WIRE CE_SUPPORT_AGENT_MODEL_CMD + run dev-3's eval = pilot live.** When #357 part-1 merges → part-2 broker drop-in. When dev-1 frees → Nitzan container e2e verify. 6. Keep seats fed (verify Working, NEVER inline). 7. Surface RESERVED/blockers; else drive.
