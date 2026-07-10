# BRIEF — dev-3 — Forge-side epic slice FORGE-2 (ce-ops#34): trigger taxonomy

Born-foreman, contained/no-egress (DO NOT push — controller harvests). Drive to READY-FOR-HARVEST. Stay in allowed paths.

## Goal
Document the FORGE-SIDE TRIGGER TAXONOMY: the catalog of forge events that can initiate governed work (issue opened/labeled, PR opened/synchronize/review, comment commands, schedule, merge_group, etc.), each mapped to its intended governed response and the guardrails. Read the forge-side automation design doc first: `docs/design/ce-forge-side-automation.md` (ON MAIN) — derive the taxonomy from it; this slice is the contract/doc, not the executor.

## Branch
`ce-forge-trigger-taxonomy` off current `origin/main`. Fresh worktree.

## Allowed paths (HARD limit)
- `docs/contracts/forge-trigger-taxonomy.md` (NEW) — the taxonomy table: trigger event → governed response → preconditions/guardrails (e.g. advisory-vs-actuating, reserved-vs-autonomous, dedup/idempotency).
- You MAY extend `docs/operations/CE_EVENT_PROTOCOL.md` if it exists and the taxonomy belongs there too (keep additions minimal + consistent).
- `.ce/changelog/ce-forge-trigger-taxonomy.md`, `.ce/pr-manifests/ce-forge-trigger-taxonomy.md`
Do NOT touch any .py, workflow, schema, ce_cli, or broker file — docs-only slice.

## Gate-coupling note
If a docs-reconciliation / index / link-check gate flags the new doc (e.g. it must be referenced from a README/index or pass a docs test), satisfy that within the allowed-paths spirit — regenerate/add the required index entry and include it; if the required target is OUTSIDE these paths, STOP and report it (don't leave validate RED). `rm -rf validators/*.egg-info validators/build` before validate (wheel-packaging footgun).

## Evidence (stop-line)
- FULL preflight GREEN: `rm -rf validators/*.egg-info validators/build; TMPDIR=/var/tmp PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr --head-ref ce-forge-trigger-taxonomy`
- Carriers via carrier_gen (dashed slug); manifest carries `- **Declared work class:** story` (or tiny if floor allows).
- Then STOP and emit: `READY-FOR-HARVEST: branch ce-forge-trigger-taxonomy, SHA <sha>, merge-base <mb>, changed paths: <list>, validate-pr GREEN.`
- DO NOT push/approve/merge. Product-lens docs: ZERO internal identities/IPs/ce-ops# in the doc body (carrier ce-ops# OK). Stay in allowed paths.
