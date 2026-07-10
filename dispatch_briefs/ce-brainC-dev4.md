# BRIEF — dev-4 — Company Brain slice BRAIN-C (ce-ops#79)

Born-foreman builder seat (contained/no-egress; DO NOT push — controller harvests). Drive to READY-FOR-HARVEST. Stay strictly inside allowed paths.

## Goal
Add a scheduled brain-ingest refresh so the vLLM recall store stays current with MEMORY.md + docs/. A script + an ops doc; no CLI/schema changes.

## Branch
`ce-brain-ingest-refresh` off current `origin/main`. Fresh worktree.

## Allowed paths (HARD limit)
- `scripts/brain-ingest-refresh.sh` (NEW) — wraps `ce brain ingest` over MEMORY.md + docs/, with drift detection (compare newest record `as_of` vs source file mtime; only re-ingest changed sources). Idempotent, safe to run on a timer.
- `docs/operations/brain-ingest-refresh.md` (NEW) — how it works + how to schedule it (systemd-user timer or cron), and that it's advisory/non-gating.
- `.ce/changelog/ce-brain-ingest-refresh.md`, `.ce/pr-manifests/ce-brain-ingest-refresh.md`
Do NOT touch ce_cli.py, broker, schemas, or any validator module — this is script + doc only.

## Notes / gate-coupling
- If a doc-index or reconciliation gate flags the new docs/operations file, regenerate whatever autogen artifact it expects AND add that file to your changed set (don't leave validate RED over an autogen sync) — report if the needed regen target is outside these paths.
- `rm -rf validators/*.egg-info validators/build` before validate to avoid the wheel-packaging footgun.

## Evidence (stop-line)
- FULL preflight GREEN: `rm -rf validators/*.egg-info validators/build; TMPDIR=/var/tmp PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr --head-ref ce-brain-ingest-refresh`
- Carriers via carrier_gen (dashed slug); manifest carries `- **Declared work class:** story` (or tiny if floor allows).
- Then STOP and emit: `READY-FOR-HARVEST: branch ce-brain-ingest-refresh, SHA <sha>, merge-base <mb>, changed paths: <list>, validate-pr GREEN.`
- DO NOT push/approve/merge. Stay in allowed paths.
