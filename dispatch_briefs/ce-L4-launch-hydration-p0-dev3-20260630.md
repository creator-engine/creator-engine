# SEED BRIEF — L4 brain launch-hydration fallback (P0) — SEAT: dev-3

**Branch:** `ce-L4-launch-hydration-fallback` off CURRENT origin/main (FIRST `git fetch origin` + worktree off origin/main). **Role:** implementer. **Work class:** declare by floor (XS/S — one function + tests). **No push auth** → commit + echo SHA; controller harvests.

## Problem (self-contained — do NOT rely on reading any private ticket)
The controller launch context is supposed to hydrate with brain recall (surface stored conventions into a fresh controller context at decision time). It currently produces **ZERO recall at every launch** because of a bug in `validators/creator_engine_validator/launch_runtime.py` → `_build_controller_brain_bootstrap()` (around lines 349-380):
- It calls `brain_recall_surface.open_surface(state_root=..., embedder_name="vllm-openai")`, which opens the DEFAULT store `recall.sqlite` (built with the deterministic embedder, dim=32). The vllm-openai embedder produces dim=4096 vectors → `_require_embedder_matches_store()` raises `BrainRecallInvalid` ("store vectors are 32-dim but the selected embedder produces 4096-dim").
- The whole block is wrapped in `except Exception: LOGGER.warning(...)` → it silently degrades to NO recall. There is no fallback to the embedder that actually MATCHES the store.
- Net: even the fully-populated 1556-chunk deterministic store (with its wikilink graph edges) is never queried.

NOTE: the wikilink graph leg AND the eval harness are ALREADY shipped + green (`brain_sqlite_vec.py` graph_expand, `brain_recall_surface.py` RRF fusion of semantic+keyword+graph, `brain_eval.py` measuring graph_lift). This P0 is ONLY the launch-hydration fallback fix — do NOT touch the graph/eval code.

## Fix (bounded — read the actual files; this is the whole P0)
**File 1 — `validators/creator_engine_validator/launch_runtime.py`, `_build_controller_brain_bootstrap()`:** Replace the single try/except around the recall path with a **two-iteration loop** over embedder options, in order: `("vllm-openai", "vllm-openai")` then `(None, "deterministic")`. For each `(embedder_name, label)`: build kwargs (include `embedder_name` ONLY when not None — None → `open_surface` defaults to `DeterministicFakeEmbedding`, which dimension-matches `recall.sqlite`), call `open_surface(**kwargs)` + `hydrate_session(...)`; on success set `payload["recall"]` (carry an `embedder=label` field) and `break`; on failure `LOGGER.warning(...)` naming the label and `continue`. If BOTH fail → set no `recall` key (preserve current behavior). The `brain_recall_surface` import already exists (~line 36); no new imports, no new modules, no v1/v3 boundary change (launch_runtime=V1 importing SHARED brain is already baselined).

**File 2 — `validators/tests/unit/test_launch_runtime.py`:** Add `test_controller_brain_bootstrap_falls_back_to_deterministic_when_vllm_unavailable(tmp_path, monkeypatch)`. Setup: write a valid genesis ledger to state_root (pattern from `test_brain_bootstrap.py`); build a `SqliteVecStore` at the default db path via `rebuild_from_source()` with 2 `RecallChunk`s using `DeterministicFakeEmbedding()` — one chunk's text contains a `[[wikilink]]` and the second is its link target (so keyword + graph legs have content). Monkeypatch `launch_runtime.brain_recall_surface.open_surface`: raise `RuntimeError` when `kwargs.get("embedder_name")=="vllm-openai"`, else call the REAL open_surface. Assert: `"recall" in payload`, `payload["recall"]["advisory"] is True`, `payload["recall"]["embedder"]=="deterministic"`, recall items non-empty, and the warning log mentions "vllm-openai" (proves it was tried first). **Do NOT change** the existing `test_controller_brain_bootstrap_falls_back_to_ssot_when_recall_unavailable` (its monkeypatch raises for ALL open_surface calls → both iterations fail → "recall" not in payload still holds) or `..._adds_advisory_recall_when_available` (first call still succeeds).

**File 3 — `validators/tests/unit/test_brain_sqlite_vec.py`:** Add `test_rebuild_invariant_preserves_graph_edges_and_keyword_results(tmp_path)`: build a store from 3 chunks (one with `[[link]]` to another), record `keyword_search(...)` + `graph_expand(...)`, call `rebuild_from_source(same_chunks, DeterministicFakeEmbedding())`, record again, assert equality before==after (rebuild-invariant: store is derived + rebuildable + stable).

## Controller decisions (locked)
- **P0 = the launch-hydration fallback ONLY.** DEFER to P1/R2: fixing the vllm GPU path to point at `recall-qwen3-8b.sqlite` (4096-dim) — that's GPU-gated (R2), out of scope. Do NOT wire real embedders or touch GPU paths.
- Deterministic fallback (keyword + graph) is the intended P0 recall — acceptable per the goal (surface a stored convention at all). `requires_egress=False` so no privacy-gate trip.

## Carrier / changelog / preflight
Carrier `.ce/pr-manifests/ce-L4-launch-hydration-fallback.md` (carrier_gen, stem==branch slug) + changelog `.ce/changelog/ce-L4-*.md`; path-set == base..HEAD. Run FULL preflight GREEN in ONE pass (`TMPDIR=/var/tmp .venv/bin/python -m pytest -q validators/tests/unit/test_launch_runtime.py validators/tests/unit/test_brain_sqlite_vec.py validators/tests/unit/test_brain_eval.py` + carrier/changelog gates). venv: `.venv/bin/python`.

## Stop line
Commit with `git commit && echo <SHA>`; report SHA + files + preflight result + confirm the existing fallback-to-ssot test still passes unchanged. Do NOT push/approve/merge, do NOT touch graph/eval/embedder code, do NOT fix the vllm path (P1/R2), no scope creep beyond the 3 files.
