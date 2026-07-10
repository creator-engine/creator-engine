# BRIEF — dev-1 — Forge-side epic slice FORGE-5 (ce-ops#34): persona catalog (docs-only)

Born-foreman, non-contained (SELF-PUSH as ce-dev-1). Drive to a green PR. Stay in allowed paths. DOCS-ONLY.

## IMPORTANT: branch off CURRENT origin/main
FIRST run `git fetch origin main` and create your worktree off `origin/main` (NOT local main) — a stale local main causes phantom-diff pollution.

## Goal
Document the forge-side PERSONA CATALOG: the set of governed worker roles the forge dispatches (architect_research, implementer, verification, reviewer, harvest_intake, ops_triage, fleet_recon) — each with purpose, authority shape (allowed tools/paths/surfaces), the ABSENT tools (least-privilege: what each role explicitly cannot do), and which role fits which work. Read `docs/design/ce-forge-side-automation.md` (on main) + the existing `.claude/agents/*.md` definitions for ground truth on each role's tools.

## Branch
`ce-forge-persona-catalog` off current `origin/main`. Fresh worktree.

## Allowed paths (HARD limit)
- `docs/contracts/forge-persona-catalog.md` (NEW) — the catalog. Describe each role's authority + absent-tools (the "no Agent tool", "read-only", "no Bash" etc. boundaries) accurately from the .claude/agents definitions. Product/contract lens.
- `.ce/changelog/ce-forge-persona-catalog.md`, `.ce/pr-manifests/ce-forge-persona-catalog.md`
Do NOT touch any .py/schema/ce_cli/broker/.claude/agents. Docs-only.

## Gate-coupling note
If a docs-reconciliation/index gate flags the new doc, add the minimal index entry AND include it; if outside these paths, STOP + report. `rm -rf validators/*.egg-info validators/build` before validate.

## Evidence
- FULL preflight GREEN: `rm -rf validators/*.egg-info validators/build; TMPDIR=/var/tmp PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr --head-ref ce-forge-persona-catalog`
- Carriers via carrier_gen (dashed slug); single carrier; manifest+body `- **Declared work class:** story` (or tiny).
- SELF-PUSH as ce-dev-1, open PR (mention ce-ops#34), report PR# + SHA. ZERO internal identities/IPs/host-paths/ce-ops# in body (carrier ce-ops# OK). No approve/merge.
