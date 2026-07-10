# BRIEF — dev-3 — Support agent Phase B: model-backend wiring + per-answer log (ce-ops#360)

Born-foreman, contained/no-egress (DO NOT push — controller harvests). Fresh branch `ce-supportagent-phaseB-model-wiring` off CURRENT origin/main (`git fetch origin main` first). Drive to READY-FOR-HARVEST GREEN; report SHA.

## Context (EMBEDDED — you cannot fetch the ticket; this is the scope)
CE's support agent (`ce ask`) has a P0 foundation already on main: `support_runtime.answer_question()` (retrieval → cite-or-refuse → zero-leak → returns SupportAnswer), a read-only `support_profile`, a docs-as-skills bundle, a system-prompt contract. **Read those modules under `validators/creator_engine_validator/` FIRST and match their existing interfaces** — do not redesign them.

Phase B makes the agent actually call a model + log usage, while keeping the model backend **pluggable** (no provider lock-in). This is durable architecture, not an MVP — channels/agency come later as adapters/extensions; you build the core seam.

## Deliverables (exactly these)
1. **Model-backend wiring (pluggable, provider-agnostic):** ensure `answer_question()` invokes the configured model via the `CE_SUPPORT_AGENT_MODEL_CMD` subprocess seam (the ConfiguredCommandModelRunner / model-runner Protocol already referenced in the code). The model command is an OPAQUE configured subprocess — **do NOT hardcode any provider** (no `openrouter`/`openai`/`anthropic`/URLs/keys in code). **Fail-closed default:** if `CE_SUPPORT_AGENT_MODEL_CMD` is unset/empty, return the existing refusal answer (as today).
2. **Per-answer usage log (append-only NDJSON):** one record per answered question with: question CLASS/category, `corpus_sha256`, model id, `accepted` (bool), `reason` code, token_spend (if available). **CRITICAL — PII: do NOT log the raw user question text or answer text.** Log a class/category only. Pick a durable, gitignored log path under the instance state dir; make it configurable.
3. **Tests against a STUB model command (no live network/model):** provide a fake model executable/script in the test that emits (a) a canned cited answer and (b) a canned refusal. Prove the full `answer_question()` path: invokes the command, parses its output, applies cite-or-refuse + zero-leak, and writes the NDJSON log record (and that PII is NOT in the log). Cover the unset-CMD fail-closed path too.

## Do NOT
- Do NOT wire a live provider or any real API key/endpoint — the live backend (a cheap-API key OR a self-hosted vLLM endpoint) is provisioned + configured SEPARATELY by the controller. You build + test the pluggable SEAM against a stub only.
- Do NOT build any Discord/Slack/channel adapter (later phase).
- Do NOT weaken cite-or-refuse / zero-leak / the read-only profile.

## Gates
- FULL `ce validate-pr` GREEN in one pass (TMPDIR=/var/tmp). Carriers (manifest via carrier_gen API, rm build/egg-info first; + changelog). One work-class line (likely `story`). Product-lens. STOP at green; report SHA. Do NOT push.
