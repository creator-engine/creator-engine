# DISPATCH BRIEF — dev-4 — ce-ops#407 N2 pin-migration SLICE 2 (forge/integrator_belt.py group)
Date: 2026-07-03 · Role: implementer · Work class: XS
Branch: `ce-407-pin-migration-s2` off FRESHLY-FETCHED origin/main (slice 1 just merged as PR #752 — you need its ledger state; fetch first, verify .ce/brain/assertions.yaml has 126 records / 83 active before starting).
Worktree: /var/tmp/wt-ce407-s2 (NOT /workspace). Venv: `.venv/bin/python -m pytest`.

## Mandate
SLICE 2 of the ratified pin-migration doctrine (embedded below, unchanged SSOT): migrate the
forge/integrator_belt.py hash pins (assertions d1b-10, d1b-11, d1b-12) to PROBE verification.
Same shape as merged slice 1 (study PR #752 in your fetched main for the exact pattern): probe
fns in brain_probe.py (LOAD-BEARING markers: specific function name + control-flow token) +
`ce brain correct` supersedes + test_ce_brain_drift.py active-count ratchet +3 (83→86).

## ⚠️ REVIEW LESSON FROM SLICE 1 (round-1 REQUEST_CHANGES — do NOT repeat)
When re-emitting the superseded prior-version snapshot records: change ONLY
`status: active→superseded` + `superseded_by`. Do NOT touch the snapshot's top-level
`evidence_ref` (or any other field) — it must stay byte-identical to the original record.
Only the NEW v-next ACTIVE records carry `evidence_ref: probe:<name>` +
`verification_method: {type: probe, probe: <name>}`.

## Scope / allowed paths
brain_probe.py (probe fns + PROBES registry) · .ce/brain/assertions.yaml (append-only supersede
chains for d1b-10/11/12 ONLY) · test_ce_brain_drift.py (ratchet) ·
.ce/changelog/ce-407-pin-migration-s2.md · carrier via carrier_gen write_carriers(base=<merge-base>)
after rm build//egg-info.

## STOP LINES
Do NOT edit forge/integrator_belt.py itself (probes READ it; the file is not yours to change).
Nothing outside scope. No push/PR — controller harvests. Doctrine-vs-reality mismatch → stop
that step + report verbatim.

## Preflight (ce-ops#303): FULL `ce validate-pr` GREEN one pass; known aarch64 env-gap failures
(install-bootstrap/wheel-bake) → capture + mark known; host preflight is the authoritative gate.

## Evidence: READY-FOR-HARVEST + branch + `git rev-parse HEAD` + validate-pr summary +
superseded IDs old→new versions + active-count 83→86 confirmation.

---
# EMBEDDED SSOT: ratified pin-migration doctrine
# ce-ops#407 — Evidence-pin doctrine (RATIFIED by Operator 2026-07-02)

Source: architect pass 2026-07-02 (read-only, grounded in .ce/wt-369-research @ 9d7ed64dd + .ce/wt-cbcs-harvest post-#743). Ratified verbatim as proposed. This file is the dispatch SSOT for migration slices.

## Classification rule (binding)
Whole-file `evidence_sha256` pins ONLY for atomic-by-design artifacts: any byte change either IS the tracked fact (signed manifests, checksum files) or the file is conventionally superseded-not-edited (ADRs) or requires a release-policy event. Everything else — files edited for reasons orthogonal to the claim — uses probe (`brain_probe.PROBES` registry) or yaml-path projection evidence scoped to the tracked fact.

## Inventory (30 active hash-pinned assertions / 23 files, all -v2 from D1b)
KEEP HASH (3): docs/delivery/VERSIONING_AND_RELEASE_POLICY.md · docs/decisions/ADR-0013-substrate-independent-authority.md (items 34, 35).
MIGRATE TO PROBE (25): pr_preflight.py (d1b-01/42/43) · forge/integrator_belt.py (d1b-10/11/12) · checks/work_sizing_floor.py · checks/install_spec_signature_guard.py · checks/ce_brain_drift.py · .claude/hooks/ce-pretooluse.sh · validators/pyproject.toml · tests/unit/test_v1_docs_reconciliation.py · tests/integration/test_install_bootstrap.py · wheelhouse/SHA256SUMS (probe asserts the coupling MECHANISM exists, not a specific sha — pinning a churning artifact's hash inverts intent) · .claude/agents/reviewer.md · .claude/agents/README.md · .claude/skills/ce-dispatch/SKILL.md · playbooks/controller/briefs/harvest.md · docs/operations/WORKER_CONTAINER_PROTOCOL.md · SEAT_LAUNCH_GOVERNANCE_RUNBOOK.md · REVIEWER_VENUE_AUTHORITY.md · PATH_MANIFEST_FIDELITY_PROTOCOL.md (d1b-02/03/41) · docs/contracts/forge-persona-catalog.md · docs/contracts/seat-class-policy.md.
MIGRATE TO PROJECTION (1): .github/workflows/ce-ops-autoclose.yml (d1b-16) — reuse the yaml-path pattern already built for validate.yml.

## Probe design template
Reuse `brain_probe.py` `_codex_pretooluse_hook` shape: probe fn reads the file, checks LOAD-BEARING markers (specific function name + control-flow token, not loose substrings), returns present/absent. Assertion: `verification_method: {type: probe, probe: <name>}`, `evidence_ref: probe:<name>`, `claim.verdict: present`. No schema/runtime change needed.

## Migration shape
~23 slices, ONE evidence-file group per PR: N× `ce brain correct` (-v3/-v4 supersedes with probe evidence) + probe fn(s) + test_ce_brain_drift.py active-count bump (+1 per corrected assertion — the count ratchet is a deliberate forcing function, KEEP). Any-order mergeable post-#743, but ALL ledger appends serialize with each other and with any in-flight supersede work.
Priority: 1) pr_preflight.py 2) forge/integrator_belt.py 3) wheelhouse/SHA256SUMS 4) ce-ops-autoclose.yml projection 5) remaining code files 6) docs.

## Separate small fixes (dispatch independently)
- Widen the volatile-workflow guard in ce_brain_drift.py (`_is_workflow_claim`/`_is_volatile_workflow_config_artifact` ~:339-347,:715-730) from `claim.subject == "workflow"` to path-based `.github/workflows/**/*.yml` regardless of subject — closes the d1b-16 bypass.
- `ce brain repin` helper: build AFTER migration, narrow scope (3 remaining hash pins + future frozen pins): recompute sha, correct_claim preserving claim/statement/scope. Addresses standing doctrine d1b-41 (hashes-must-be-recomputed).

## Risks (accepted at ratification)
Probes catch the tracked fact, not adjacent behavioral drift — mitigate with load-bearing markers; probes are one signal among tests+review. Probe-fn meta-drift (nothing verifies a probe still measures what its assertion claims) flagged as follow-up, out of scope. Doctrine-coverage ratchet (#737) unaffected (keys off evidence_ref presence, not verification type; only 2/23 files inside governed docs/contracts tree).
