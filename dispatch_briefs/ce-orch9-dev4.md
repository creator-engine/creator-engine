# BRIEF — dev-4 — Orchestrator epic slice ORCH-9 (ce-ops#616): read-only cockpit

Born-foreman, contained/no-egress (DO NOT push — controller harvests). Drive to READY-FOR-HARVEST. Stay in allowed paths.

## Goal
Add a READ-ONLY `ce orchestrator status` command that renders the orchestrator's runtime state from the just-shipped record schemas (#628) — checkpoints, territory-maps, harvest-packets, operator-decision-queue. PURE RENDER: it reads + validates + displays; it has NO actuators (no dispatch, merge, gate, approve, arm, or any mutation). This is the observability surface for the orchestrator role (the #633 role-contract describes the records).

## Branch
`ce-orchestrator-cockpit` off CURRENT origin/main (run `git fetch origin main` first). Fresh worktree.

## Scope
- Read the 4 schemas `validators/creator_engine_validator/schemas/orchestrator-*.schema.yaml` + `orchestrator_records.py` (validator) + `docs/contracts/orchestrator.md` (#633) for the record shapes.
- Add a new module `validators/creator_engine_validator/orchestrator_status.py` that reads orchestrator runtime records from a state dir (e.g. `.ce/state/orchestrator/{checkpoints,territory-maps,harvest-packets,operator-decisions}/*.json`), validates each against its schema via `orchestrator_records.validate_orchestrator_record(kind, record)`, and returns a structured status summary. GRACEFUL when no records / dir absent (returns an empty/none summary, never raises).
- Add a `ce orchestrator status` subcommand (NEW `orchestrator` command group) to ce_cli.py — parser + handler + dispatch — that prints the summary (human + `--json`). READ-ONLY: the handler may ONLY read+render; it must not call any dispatch/merge/gate/actuator function.

## Allowed paths (HARD limit)
- `validators/creator_engine_validator/orchestrator_status.py` (NEW)
- `validators/creator_engine_validator/ce_cli.py` (new orchestrator group/subcommand only — do NOT touch automerge/brain/other groups)
- `validators/tests/unit/test_orchestrator_status.py` (NEW)
- DOCS-RECONCILIATION (a NEW `ce` group REQUIRES these — regenerate + include them, or validate will RED): `.ce/reference/cli.generated.md` (regen via `scripts/gen_cli_reference.py --write`), `README.md` (add the orchestrator group), and add the group to the registry set in `validators/tests/unit/test_v1_docs_reconciliation.py`.
- `.ce/changelog/ce-orchestrator-cockpit.md`, `.ce/pr-manifests/ce-orchestrator-cockpit.md`
Do NOT touch the broker, cred_injection_proxy, forge/ actuator/automerge, or any other group.

## Evidence (stop-line)
- FULL preflight GREEN: `rm -rf validators/*.egg-info validators/build; TMPDIR=/var/tmp PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr --head-ref ce-orchestrator-cockpit`
  (New ce group trips test_v1_docs_reconciliation + cli_reference_autogen_sync — the regen above resolves them; if a needed regen target is outside these paths, STOP + report.)
- Carriers via carrier_gen (dashed slug); single carrier; manifest `- **Declared work class:** feature` (new group + module + tests + docs).
- STOP and emit: `READY-FOR-HARVEST: branch ce-orchestrator-cockpit, SHA <sha>, merge-base <mb>, changed paths: <list>, validate-pr GREEN.`
- HARD STOP-LINE: READ-ONLY cockpit — NO dispatch/merge/gate/approve/arm/mutation anywhere. ZERO internal identities/IPs/host-paths in doc/code bodies. No push. Stay in allowed paths.
