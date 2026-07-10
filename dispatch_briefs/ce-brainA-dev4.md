# BRIEF — dev-4 — Company Brain slice BRAIN-A (ce-ops#79 productization)

You are a born-foreman builder seat. Drive this slice to READY-FOR-HARVEST. You may use subagent threads, but every change MUST stay inside the allowed paths. You are contained/no-egress: DO NOT push — the controller harvests. Commit and emit the harvest signal with the SHA.

## Goal
Wire the already-shipped semantic recall (vLLM Qwen3-8B embedder + hybrid recall surface) into the CONTROLLER LAUNCH context injection. Today `_build_controller_brain_bootstrap()` only emits the deterministic SSOT assertion ledger; the semantic recall layer is fully implemented but NOT surfaced at launch. Close that gap, additively and fail-safe.

## Branch
`ce-brain-hydration-launch` based off current `origin/main` (tip 83907bb7). Create a fresh worktree.

## Allowed paths (HARD territory limit — touch nothing else)
- `validators/creator_engine_validator/launch_runtime.py`
- `validators/creator_engine_validator/brain_bootstrap.py`
- `validators/tests/unit/test_*` — ONLY new/extended tests for this slice (e.g. test_launch_runtime_brain_hydration.py)
- `.ce/changelog/ce-brain-hydration-launch.md` (new)
- `.ce/pr-manifests/ce-brain-hydration-launch.md` (new)
Do NOT touch the egress broker, cred_injection_proxy, forge/, or any recall-surface module itself (consume its public API only).

## Scope
1. In `validators/creator_engine_validator/launch_runtime.py`, extend `_build_controller_brain_bootstrap()` (≈L330) so that, IN ADDITION to the existing deterministic `assertions` payload, it OPTIONALLY folds in a top-K semantic recall slice:
   - Call `brain_recall_surface.open_surface(embedder_name="vllm-openai", ...)` then `hydrate_session(context=<the launch context/seat role+repo>, top_k=5, allow_confidential_egress=False)`.
   - `allow_confidential_egress=False` is REQUIRED (safe default; confidential-scoped MEMORY entries must NOT be embedded through the egress embedder — the surface's `_guard_query_egress` enforces this).
   - Add the result under a NEW `"recall"` key in the brain payload, ALONGSIDE (never replacing) the existing `assertions`/SSOT section. The SSOT precedence invariant must be preserved: SSOT assertions remain authoritative; recall pointers are advisory hints.
2. GRACEFUL FALLBACK (fail-safe, not fail-closed-blocking): if the vLLM endpoint (http://127.0.0.1:8989) is unreachable/offline, or the recall store/embedder errors, the function must still return the SSOT-only payload exactly as today (catch + log, no raise). Launch must never break because recall is down.
3. Tests: add a unit test covering BOTH paths — (a) endpoint/surface available → payload contains a populated `recall` section + the `assertions` section; (b) surface unavailable (monkeypatch open_surface to raise / endpoint absent) → payload == SSOT-only, no exception. Assert the recall section is advisory (does not override assertions).

## Evidence required (stop-line)
- FULL local preflight GREEN in ONE pass:
  `rm -rf validators/*.egg-info validators/build; TMPDIR=/var/tmp PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr --head-ref ce-brain-hydration-launch`
- Generate carriers (DASHED slug) via carrier_gen against the origin/main merge-base; PR-manifest MUST carry the line `- **Declared work class:** story`.
- Then STOP. Emit exactly:
  `READY-FOR-HARVEST: branch ce-brain-hydration-launch, SHA <sha>, merge-base <mb>, changed paths: <list>, validate-pr GREEN.`
- DO NOT push, approve, merge, or touch any other lane. No arming/flip/release.
