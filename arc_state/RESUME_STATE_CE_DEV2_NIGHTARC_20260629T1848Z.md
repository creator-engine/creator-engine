# RESUME STATE — CE-DEV-2 Orchestrator — NIGHT-SHIFT ARC — 2026-06-29 ~18:48Z

> NEWEST. Supersedes 1816Z/1740Z. Open this + MEMORY.md FIRST. Night-arc = balanced completion of all in-flight lanes + arming proof + automation-scaling, **FULL AUTONOMOUS** (standing G1–G5, Operator-ratified this session): drive/review/gate/merge; surface only RESERVED/hard-blockers; checkpoint for morning. Author≠approver always.

## AUTH
overwatch: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Approve as ce-dev-2: `GH_TOKEN=$(cat ~/.ce-keys/ce-dev-2.pat) gh pr review <n> --approve`. queue-daemon pid 43010 auto-merges approved+green (logs `~/ce-wall-daemon.log`). Routing: reviewer/harvest/implementer/architect=sonnet, recon/triage/verification=haiku, Opus=controller.

## 🟣 GATE QUEUE (live — re-approve/merge as CI greens)
- **#653** Tranche-2 os-native exec (fail-closed). Carrier-slug fixed → new head **fd3feac4d**. My approval was dismissed by the fix push → **RE-APPROVE when its "Validate governance artifacts" check is GREEN** (one-shot watcher `b4tiyl6sg` armed → notifies on conclusion). Reviewer already verified clean (no unsandboxed launch path). Latent Tranche-3 note: egress test match-string will need update when the unconditional raise is removed.
- **#655** onboarding RED-G-4 guidance (dev-1). **APPROVED** (reviewer confirmed RED-G-4 still refuses, guidance steps correct) → daemon merges when CI green. No action.
- **#656** Phase B support model wiring (harvest of dev-3). **Reviewer `a40fccbbd` RUNNING** → on APPROVE, approve as ce-dev-2 → gate. Focus: no hardcoded provider / fail-closed / PII-safe NDJSON log (class not raw text).
- MERGED this session: **#654** (installer uv trust, incl. deliberate 0.2.0 mirror backport — policy ticket ce-ops#361 filed), #651 (onboard RED-G-6 unblock), #652 (canary), #645–650.

## 🔵 SEATS (all Working as of 18:48Z) — extraction = git bundle out of container (NOT push); herdr/tmux pointer+sha
- **dev-1** (non-contained VPS, self-push) → **OpenRouter model-command adapter** (ce-ops#360 backend): NEW standalone artifact matching `CE_SUPPORT_AGENT_MODEL_CMD` JSON-over-stdin→stdout-answer contract (in main `ConfiguredCommandModelRunner`), fail-closed, live-smoke + CI-safe mocked test. Branch `ce-support-openrouter-adapter`. Brief `~/ce-briefs/ce-360-openrouter-adapter-dev1.md`.
- **dev-3** (contained ce-vps-codex) → **zero-leak eval harness** (release-blocking), NEW FILES ONLY. Branch `ce-supportagent-zeroleak-eval`.
- **dev-4** (contained ce-dgx-codex) → **ce-ops#357 part-1** broker-decouple (stable checkout, not seat tree). Branch `ce-357-broker-decouple`. (Part-2 = dev-4 broker run-mode drop-in = MY ops, deferred until part-1 lands.)

## 🟢 SUPPORT PILOT — critical path now CONVERGING
P0(#644 main) → **Phase B (#656 gating now)** → backend = **dev-1 OpenRouter adapter (building)** → point `CE_SUPPORT_AGENT_MODEL_CMD` at the adapter (key `~/.ce-keys/openrouter.env`) → dev-3 zero-leak eval → live `ce ask`. Contract: JSON(SupportRequest.to_dict()) on stdin, answer on stdout, exit0; non-zero/timeout→refusal (fail-closed). Claude BANNED as backend. When #656 + adapter both land: WIRE the seam + run eval = pilot live.

## 🟡 ONBOARDING (Nitzan, today) — nearly handoff-ready
#651 (RED-G-6 unblock) MERGED + **F5 re-verified PASS**. #655 (RED-G-4 actionable guidance) APPROVED/merging. #654 (installer) MERGED. After #655 lands → run FULL Nitzan e2e verify (Mac-container runbook → brain init → onboard → launch) in a fresh container; fix any residual doc/welcome.md gap; mark handoff-ready.

## 🩺 INFRA
- Brain `vllm-qwen3-embed` :8989 RESTORED this resume (had died 17:47Z) — serving. Watch for repeat death.
- Daemon 43010 ALIVE. Crons seat-check:00 poll-devs:05 conveyor-tend:30 hourly:47. Watchers: board b9aipnn3b + bh8s12igt, seat bs2rmjt2y + bxa44s2dn (redundant, harmless), #653 CI b4tiyl6sg.
- **HARVEST GOTCHAS** (memory [[ce-harvest-carrier-slug-must-match-branch]]): (1) carrier stem MUST == branch_slug(pushed head) or CI path-manifest gate fails closed (local validate-pr misses it) — push under carrier's branch name OR git-mv carriers + regen; (2) `carrier_gen.write_carriers` OMITS the `- **Declared work class:** <x>` line — must re-add manually or the gate fails.

## 🟠 SCALING QUEUE (CEO-mode #291 CLOSED — its policy IS the live arming)
forge autonomy/triage (needs design pass) · fleet-wide Surface-B = ce-ops#357 (dev-4 part-1 in flight) · company-brain · expand auto-merge confidence (gated). Tickets filed this session: ce-ops#357/358/359/360/361. Probe territory + not-already-landed before dispatch.

## ON RESUME
1. Read this + MEMORY. 2. `gh pr list` reconcile (#653/#655/#656 merged? new seat branches: adapter/eval/#357?). 3. Verify watchers + daemon 43010 + brain :8989. 4. #653: re-approve if green+unapproved. #656: gate if reviewer approved. 5. After Phase B (#656)+adapter land → wire CE_SUPPORT_AGENT_MODEL_CMD at adapter + run eval. After #357 part-1 lands → part-2 broker drop-in. After #655 lands → Nitzan e2e verify. 6. Keep seats fed (verify Working, NEVER inline). 7. Surface RESERVED/blockers; else drive.
