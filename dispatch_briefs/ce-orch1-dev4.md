# BRIEF — dev-4 — Orchestrator epic slice ORCH-1 (ce-ops#616): role contract

Born-foreman, contained/no-egress (DO NOT push — controller harvests). Drive to READY-FOR-HARVEST. Stay in allowed paths.

## Goal
Canonize the CE Orchestrator role CONTRACT — promote the design into a durable contract doc. Sources (ON MAIN, read first): `docs/design/ce-orchestrator-agent.md` (the 9-step lifecycle, invariants, worker/seat model, runtime records) and `docs/decisions/ADR-0013-substrate-independent-authority.md` (the autonomous-vs-reserved action taxonomy + substrate-independence). The existing `docs/contracts/orchestrator.md` is a STUB — fill it.

## Branch
`ce-orchestrator-role-contract` off current `origin/main`. Fresh worktree.

## Allowed paths (HARD limit)
- `docs/contracts/orchestrator.md` (fill the stub: role definition; the 9-step lifecycle; invariants — no-inline-implementation, author≠reviewer, territory-aware-before-dispatch-and-merge, merge needs review+green+ratification, reserved-actions-HALT, idle-seat-is-a-fault; the autonomous-vs-reserved action taxonomy from ADR-0013; the 4 runtime records from #628's schemas referenced by name)
- `.ce/changelog/ce-orchestrator-role-contract.md`, `.ce/pr-manifests/ce-orchestrator-role-contract.md`
Docs-only. Do NOT touch any .py/schema/workflow/ce_cli/broker.

## Gate-coupling note
If a docs-reconciliation/index/contract-sync gate flags the change (e.g. a contract must be listed in an index, or test_v1_docs_reconciliation), regenerate/add what it requires AND include that file; if the required target is outside these paths, STOP and report. `rm -rf validators/*.egg-info validators/build` before validate.

## Evidence (stop-line)
- FULL preflight GREEN: `rm -rf validators/*.egg-info validators/build; TMPDIR=/var/tmp PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr --head-ref ce-orchestrator-role-contract`
- Carriers via carrier_gen (dashed slug); manifest carries `- **Declared work class:** story`.
- STOP and emit: `READY-FOR-HARVEST: branch ce-orchestrator-role-contract, SHA <sha>, merge-base <mb>, changed paths: <list>, validate-pr GREEN.`
- DO NOT push/approve/merge. Product/internal-lens doc but ZERO internal identities/IPs/host-paths/ce-ops# in the body (carrier ce-ops# OK; this is docs/contracts, keep it clean). Stay in allowed paths.
