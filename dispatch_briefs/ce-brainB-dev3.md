# BRIEF — dev-3 — Company Brain slice BRAIN-B (ce-ops#79 productization)

You are a born-foreman builder seat (contained/no-egress; DO NOT push — the controller harvests). Drive to READY-FOR-HARVEST. You may use subagent threads; stay strictly inside the allowed paths.

## Goal
Add an OFFLINE recall eval harness so we can measure keyword vs semantic recall quality on representative controller queries. Pure offline — no vLLM endpoint needed for the eval itself (use deterministic/mock embedding legs).

## Branch
`ce-brain-eval-harness` off current `origin/main` (tip 83907bb7). Fresh worktree.

## Allowed paths (HARD territory limit)
- `validators/creator_engine_validator/brain_eval.py` (NEW)
- `validators/tests/unit/test_brain_eval.py` (NEW)
- `validators/creator_engine_validator/ce_cli.py` — ONLY the `brain` command group (around lines 860-1050; add a `brain eval` subcommand). DO NOT touch the automerge-decide section (~line 1456) or any other group.
- `.ce/changelog/ce-brain-eval-harness.md`, `.ce/pr-manifests/ce-brain-eval-harness.md`

## Scope
1. `brain_eval.py`: a pure offline eval module with a small golden set — ~10-20 representative controller-context query strings + a small fixture document set (a few markdown snippets). Run BOTH recall legs over the fixtures:
   - the deterministic FTS5/keyword leg (use the existing `DeterministicFakeEmbedding` or equivalent keyword stand-in already in the brain modules);
   - a semantic leg using a MOCK/deterministic embedding (no live vLLM call).
   Compute recall@K (e.g. K=3,5) for each leg and produce a structured comparison report (dict/dataclass).
2. `ce brain eval` CLI subcommand (in the brain group of ce_cli.py): runs the harness and prints the structured report. Offline-safe — must not require the vLLM endpoint.
3. `test_brain_eval.py`: assert the harness runs end-to-end on the fixtures, returns recall@K metrics for both legs, and that the report shape is stable. Real asserts (not always-pass).

## Evidence required (stop-line)
- FULL local preflight GREEN one pass (clean the build artifacts FIRST to avoid the egg-info/wheel-packaging footgun):
  `rm -rf validators/*.egg-info validators/build; TMPDIR=/var/tmp PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr --head-ref ce-brain-eval-harness`
  (If `test_schema_packaging_wheel.py` fails, it is stale-artifact contamination — re-run after `rm -rf validators/*.egg-info validators/build` in a clean state.)
- Carriers via carrier_gen (DASHED slug); PR-manifest carries `- **Declared work class:** story`.
- Then STOP. Emit exactly:
  `READY-FOR-HARVEST: branch ce-brain-eval-harness, SHA <sha>, merge-base <mb>, changed paths: <list>, validate-pr GREEN.`
- DO NOT push/approve/merge. Offline-only (no live endpoint). Stay within allowed paths; touch only the brain group of ce_cli.py.
