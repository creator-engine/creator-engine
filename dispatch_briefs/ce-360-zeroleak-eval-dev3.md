# BRIEF — dev-3 — Support agent zero-leak eval harness (ce-ops#360, release-blocking)

Born-foreman, contained/no-egress (DO NOT push — controller harvests). Fresh branch `ce-supportagent-zeroleak-eval` off CURRENT origin/main (`git fetch origin main` first). Drive to READY-FOR-HARVEST GREEN; report HEAD SHA.

## Context (EMBEDDED — you cannot read the ticket; this IS the scope)
CE's support agent (`ce ask`) has a P0 foundation on main: `support_runtime.answer_question()` (retrieval → cite-or-refuse → zero-leak → returns `SupportAnswer`), a read-only `support_profile`, a product-lens docs corpus. **Read those modules under `validators/creator_engine_validator/` FIRST and match their existing interfaces — do not modify them.**

"Zero-leak" = the support agent must NEVER surface CE-internal/confidential content (ce-ops# issue refs, internal infra/identities, private playbook detail, secrets) into a user-facing answer; it cites public product docs or refuses. This is a property of the corpus + retrieval + refusal path and is testable against a STUB model (no live backend needed).

## Why now / why standalone
This is the **release-blocking eval** for the support pilot. Build it as a durable, reusable harness that runs a battery of real CE questions and asserts zero-leak + correct cite-or-refuse. Point-at-stub now; the same harness gets pointed at the real backend (OpenRouter/vLLM) later via config — so build the seam right once, no teardown.

## Deliverables — NEW FILES ONLY (critical: do NOT edit support_runtime.py / support_profile / any existing module — another PR is in flight on those)
1. **Eval harness module** (new file, e.g. `validators/creator_engine_validator/support_eval.py`): a runner that takes a list of eval cases (question + expected disposition: answered-with-citation | refused) and a model-command seam (reuse the existing `CE_SUPPORT_AGENT_MODEL_CMD` subprocess contract — do NOT hardcode any provider), invokes `answer_question()`, and produces a structured report (per-case: disposition, citations, leak-violations[], pass/fail) plus an aggregate (counts, any leak = hard FAIL).
2. **Leak-detector** (in the same new module): given an answer + the known set of confidential markers (ce-ops# pattern, internal hostnames/identities, private-playbook tokens — define a conservative, configurable denylist + heuristics), flag any leak. Err toward flagging (false-positive-safe).
3. **Eval case fixtures** (new files under a new dir, e.g. `validators/tests/fixtures/support_eval/`): ≥8 realistic CE product questions — mix of (a) answerable-from-public-docs and (b) ones that probe for internal/confidential info and MUST be refused or answered without leaking.
4. **Tests** (new file, e.g. `validators/tests/unit/test_support_eval.py`): drive the harness against a STUB model command (fake executable emitting canned answers — one clean cited answer, one that ATTEMPTS to leak an internal ref → harness must catch it as a hard FAIL, one refusal). Prove: harness runs end-to-end, leak-detector catches the planted leak, clean cases pass, aggregate FAILs if any leak present.

## Do NOT
- Do NOT modify `support_runtime.py`, `support_profile`, or any existing support module (in-flight PR owns them). New files only.
- Do NOT wire a live provider/API key/endpoint (controller configures the real backend separately).
- Do NOT weaken or bypass cite-or-refuse / zero-leak.

## Gates
- FULL `ce validate-pr` GREEN in ONE pass (`TMPDIR=/var/tmp`). Carriers: manifest via `carrier_gen.write_carriers(base=<merge-base>)` API (rm build/egg-info first) + `.ce/changelog/<slug>.md`. PR body work-class line (likely `story`). Product-lens. STOP at green; report SHA. Do NOT push.
