# BRIEF — dev-1 — Support agent OpenRouter model-command adapter (ce-ops#360 backend)

Non-contained, SELF-PUSH as ce-dev-1. Fresh branch `ce-support-openrouter-adapter` off CURRENT origin/main (`git fetch origin main` first; switch off your #655 branch). Drive to a GREEN PR; self-push, do NOT merge/approve.

## Why this lane / why dev-1
CE's support agent (`ce ask`) calls its model through a pluggable subprocess seam `CE_SUPPORT_AGENT_MODEL_CMD` (already in main). We need the concrete OpenRouter backend command that seam points at, for the pilot. You (non-contained) can make LIVE OpenRouter calls to smoke-test it — contained seats cannot. This is on the support-pilot critical path. Claude is BANNED as backend (Anthropic prohibits subscription/SDK in 3rd-party harness); OpenRouter cheap-API is the ratified pilot backend.

## The EXACT contract (read it yourself, do not guess)
Read `validators/creator_engine_validator/support_runtime.py` — class `ConfiguredCommandModelRunner` (~line 183) + `SupportRequest` + its `to_dict()`. The contract your command MUST satisfy:
- Input: the runner pipes `json.dumps(SupportRequest.to_dict(), sort_keys=True)` on **STDIN**.
- Output: print the model's answer TEXT to **STDOUT** and **exit 0**. The runner returns `stdout.strip()`.
- Fail-closed: ANY error → exit NON-ZERO (the runner maps non-zero/timeout/OSError to the existing refusal answer). Honor `CE_SUPPORT_AGENT_MODEL_TIMEOUT` (default 120s).
- Match the real `SupportRequest.to_dict()` field names when extracting the question + any retrieved context/citations — read the dataclass, do not assume.

## Deliverable — NEW standalone artifact (do NOT edit support_runtime.py or any existing support module)
1. A committed, tested adapter command, e.g. `tools/support-agent/openrouter_model_cmd.py` (pick a sensible path; make it executable + documented). It:
   - Reads the JSON request from stdin per the contract above; extracts question + context.
   - Calls the OpenRouter chat-completions API (`https://openrouter.ai/api/v1/chat/completions`) with a configurable model (env e.g. `CE_OPENROUTER_MODEL`, default a cheap capable model — pick one current/available, document it) and the API key from env `CE_OPENROUTER_API_KEY` (NEVER hardcode a key; NEVER log the key or the full request).
   - Prints ONLY the answer text to stdout, exit 0 on success; exit non-zero with a stderr reason on ANY failure (missing key, HTTP error, timeout, bad response) — fail-closed.
   - Builds a sane system+user prompt from the request (you may keep it minimal; the governed cite-or-refuse/zero-leak live in CE, not here).
2. **Live smoke test** (you run it, include evidence in the PR description, NOT as a CI test): pipe a sample SupportRequest JSON into the command with the real key from `~/.ce-keys/openrouter.env`, show it returns a sensible answer + exit 0, and show a forced-error case exits non-zero. Do NOT commit the key or any live response containing it.
3. **Unit test (CI-safe, NO network):** mock the OpenRouter HTTP call; assert (a) well-formed request → answer on stdout + exit 0, (b) missing key → non-zero exit (fail-closed), (c) HTTP error/non-200 → non-zero exit, (d) the key is never written to stdout. Use the real stdin JSON shape.

## Do NOT
- Do NOT edit `support_runtime.py`, `support_profile`, `support_eval.py`, or any existing support module (other lanes in flight — dev-3 owns the eval).
- Do NOT touch `install.sh`, `ce_onboard.py` (your #655), `os_native_backend.py`, broker files.
- Do NOT hardcode/commit the API key; do NOT log secrets or full user content.
- Do NOT add the live OpenRouter call to any CI-run test (network-free CI only).

## Gates
- FULL `ce validate-pr` GREEN in ONE pass (`TMPDIR=/var/tmp`). Carriers: manifest via `carrier_gen.write_carriers(base=<merge-base>)` API (rm build/egg-info first) + `.ce/changelog/<slug>.md` — carrier slug MUST equal branch slug `ce-support-openrouter-adapter`. PR body work-class line (likely `story`). Product-lens. Report PR # + head SHA. Self-push, do NOT merge.
