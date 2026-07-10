# BRIEF — dev-4 — Orchestrator epic slice: runtime-record schemas (ce-ops#616 epic)

You are a born-foreman builder seat (contained/no-egress; DO NOT push — the controller harvests). Drive to READY-FOR-HARVEST. Subagent threads OK; stay strictly inside the allowed paths.

## Goal
Specify the Orchestrator's 4 runtime-record JSON schemas as the durable contract for its state artifacts. The CE Orchestrator Agent design doc (`docs/design/ce-orchestrator-agent.md`, ON MAIN — read it first) names four runtime records: **checkpoint**, **territory-map**, **harvest-packet**, **operator-decision**. Turn each into a validated schema with a small validation helper + tests.

## Branch
`ce-orchestrator-record-schemas` off current `origin/main` (tip 83907bb7). Fresh worktree.

## Allowed paths (HARD territory limit)
- `validators/creator_engine_validator/schemas/orchestrator-checkpoint.schema.yaml` (NEW)
- `validators/creator_engine_validator/schemas/orchestrator-territory-map.schema.yaml` (NEW)
- `validators/creator_engine_validator/schemas/orchestrator-harvest-packet.schema.yaml` (NEW)
- `validators/creator_engine_validator/schemas/orchestrator-operator-decision.schema.yaml` (NEW)
- `validators/creator_engine_validator/orchestrator_records.py` (NEW — a small self-contained validation module that loads + validates a record dict against the right schema; do NOT wire it into any existing registry/CLI in this slice)
- `validators/tests/unit/test_orchestrator_records.py` (NEW)
- `.ce/changelog/ce-orchestrator-record-schemas.md`, `.ce/pr-manifests/ce-orchestrator-record-schemas.md`
Do NOT touch ce_cli.py, the broker, cred_injection_proxy, or any existing module. This slice is schema + standalone validator + tests ONLY.

## Scope
1. PROBE first (verify-not-already-landed): confirm none of these 4 schema files already exist on main. If any exists, STOP and report.
2. Read the design doc's runtime-record section; derive each record's fields/shape from it (e.g. checkpoint: arc/timestamp/in-flight/seats/board/next-lane; territory-map: claims/paths/seat; harvest-packet: branch/sha/merge-base/changed-paths/validate-status; operator-decision: question/options/decision/ratified-by/timestamp). Where the doc is silent, choose sensible required/optional fields and document them in the schema `description`s. Use JSON-Schema (draft 2020-12) expressed as YAML, mirroring the existing `schemas/*.schema.yaml` conventions in the repo.
3. `orchestrator_records.py`: a small module exposing e.g. `validate_orchestrator_record(kind, record) -> None` (raises on invalid) that loads the matching schema and validates. Self-contained; no imports from forge/ or broker.
4. `test_orchestrator_records.py`: for each of the 4 kinds, a valid record passes and at least one invalid record (missing required field / wrong type) raises. Real asserts.

## Evidence required (stop-line)
- FULL local preflight GREEN one pass (clean artifacts first):
  `rm -rf validators/*.egg-info validators/build; TMPDIR=/var/tmp PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr --head-ref ce-orchestrator-record-schemas`
  (If `test_schema_packaging_wheel.py` fails, it's stale-artifact contamination — re-run after the rm.)
- Carriers via carrier_gen (DASHED slug); PR-manifest carries `- **Declared work class:** feature` (4 schemas + module + tests).
- Then STOP. Emit exactly:
  `READY-FOR-HARVEST: branch ce-orchestrator-record-schemas, SHA <sha>, merge-base <mb>, changed paths: <list>, validate-pr GREEN.`
- DO NOT push/approve/merge. Schema+validator+tests only — no CLI wiring, no actuation. Stay within allowed paths.
