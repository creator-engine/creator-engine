# BRIEF — dev-1 — Forge-side epic slice FORGE-3 (ce-ops#34): workflow-as-artifact catalog (docs-only)

Born-foreman, non-contained (SELF-PUSH as ce-dev-1). Drive to a green PR. Stay in allowed paths. DOCS-ONLY this slice (no schema/code — keep it low-coupling).

## Goal
Document the WORKFLOW-AS-ARTIFACT CATALOG: the set of named, reusable governed workflows the forge can run (e.g. review→gate, harvest→preflight→PR, dispatch→watch→harvest, autoreview-decide), each as a catalog entry — name, purpose, inputs, the governed steps, autonomous-vs-reserved classification, and idempotency/dedup notes. Read `docs/design/ce-forge-side-automation.md` (ON MAIN) for the source intent.

## Branch
`ce-forge-workflow-catalog` off current `origin/main`. Fresh worktree.

## Allowed paths (HARD limit)
- `docs/contracts/workflow-catalog.md` (NEW) — the catalog. Reference (by name) the orchestrator action-taxonomy (ADR-0013) and the trigger taxonomy (if FORGE-2's doc has landed; if not, reference it generically). Defer any JSON-schema formalization to a follow-up slice — this is the prose contract.
- `.ce/changelog/ce-forge-workflow-catalog.md`, `.ce/pr-manifests/ce-forge-workflow-catalog.md`
Do NOT touch any .py/schema/workflow/ce_cli/broker. Docs-only.

## Gate-coupling note
If a docs-reconciliation/index/link gate flags the new doc, satisfy it (add the index entry etc.) within scope; if the required target is outside these paths, STOP and report. `rm -rf validators/*.egg-info validators/build` before validate.

## Evidence
- FULL preflight GREEN: `rm -rf validators/*.egg-info validators/build; TMPDIR=/var/tmp PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr --head-ref ce-forge-workflow-catalog`
- Carriers via carrier_gen (dashed slug); manifest+body carry `- **Declared work class:** story` (or tiny).
- SELF-PUSH as ce-dev-1, open PR (mention ce-ops#34), report PR# + SHA. Product/internal-lens doc but ZERO internal identities/IPs/host-paths/ce-ops# in the BODY (carrier ce-ops# OK). Do NOT approve/merge.
