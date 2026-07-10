# DISPATCH BRIEF — dev-4 — ce-ops#407 N2 pin-migration SLICE 1 (pr_preflight.py)
Date: 2026-07-03 · Role: implementer · Work class: XS
Branch: `ce-407-pin-migration-s1` (off freshly-fetched origin/main; if fetch fails, report it and use your latest local origin/main — controller reconciles at harvest)
Worktree: create under `/var/tmp/wt-ce407-s1` (NOT /workspace). Venv has no activate — use `.venv/bin/python -m pytest`.

## Mandate
Execute SLICE 1 ONLY of the ratified evidence-pin migration doctrine (full doctrine embedded below — it is the SSOT for the mechanics): migrate the `pr_preflight.py` hash pins (assertions d1b-01, d1b-42, d1b-43) from hash-pin to PROBE verification.

## Scope / allowed paths
- Probe functions: add to the brain probe module (follow the existing `_codex_pretooluse_hook` probe shape exactly — probe fn reads the target file, checks LOAD-BEARING markers: specific function name + control-flow token, NOT loose substrings, returns present/absent).
- Ledger: N× `ce brain correct` supersedes (v-next) for d1b-01/42/43 with `verification_method: {type: probe, probe: <name>}`, `evidence_ref: probe:<name>`, `claim.verdict: present`. ONE evidence-file group (pr_preflight.py) in this PR — one supersede chain per assertion, all in this single PR is fine (they share the evidence file), per doctrine.
- `test_ce_brain_drift.py`: active-count ratchet bump (+1 per corrected assertion — the ratchet is a deliberate forcing function, KEEP it).
- Changelog: `.ce/changelog/ce-407-pin-migration-s1.md` (required by CI gate).
- Carrier: regenerate via the carrier_gen API — `write_carriers(base=<merge-base vs origin/main>)` — never hand-edit. Remove build//egg-info dirs first.

## STOP LINES
- Do NOT touch `forge/integrator_belt.py` (that is slice 2, not yours today; any edit to it breaks other d1b pins).
- Do NOT touch files outside the scope list. No workflow files, no automerge files.
- No push, no PR: you have no push auth. Controller harvests.
- If the doctrine below and reality disagree (e.g., probe module name differs), STOP that step and report the discrepancy verbatim in your done-report rather than improvising.

## Preflight (standing directive ce-ops#303)
Run the FULL local validator preflight (`ce validate-pr`, CI parity) in ONE pass before commit-for-harvest; do not discover gates via CI. Known in-container env gaps on this seat (aarch64): install-bootstrap / wheel-bake tests may fail for environment reasons — if they fail, capture the output and mark them as the known env-gap in your report; the host-side preflight is the authoritative gate.

## Evidence required in your done-report
READY-FOR-HARVEST + branch name + `git rev-parse HEAD` SHA (echo it — a done-report without a verifiable commit SHA is NOT done) + validate-pr summary (pass/fail per gate) + the list of superseded assertion IDs with old→new versions + active-count old→new.

---
# EMBEDDED SSOT: ratified pin-migration doctrine (ce407-evidence-pin-doctrine-RATIFIED.md)
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
