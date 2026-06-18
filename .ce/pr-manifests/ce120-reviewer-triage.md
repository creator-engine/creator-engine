# PR path manifest - ce120-reviewer-triage - reviewer-triage Phase 1-2

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce120-reviewer-triage
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. The carrier lists itself. The repo-wide `path_manifest_fidelity`
scan requires the declared count and SHA256 to match the fenced block.

Ratified gate:
Operator-ratified ce-ops#120 reviewer-triage Phase 0-2 build, relayed by the
CE-DEV-2 Controller on 2026-06-18. Branch `ce120-reviewer-triage`; plan-only,
no source-host mutation, commit-local and no push.

Amendment:
Operator-ratified ce-ops#120 amendment on 2026-06-18. The additive delta composes
reviewer triage with ce-ops ADR-0003 isolation-domain tiers, ce-ops ADR-0004
containment eligibility, CE58 live-identity guard preservation, and #34
ticket-triage separation.

Per-file purpose (closed path-set - 25 paths):
- **`.ce/pr-manifests/ce120-reviewer-triage.md`** *(A)* - this carrier.
- **`.ce/changelog/ce120-reviewer-triage.md`** *(A)* - per-PR changelog fragment.
- **`schemas/reviewer-registry.schema.yaml`** *(A)* - governed reviewer registry schema.
- **`schemas/reviewer-triage-decision.schema.yaml`** *(A)* - auditable triage decision schema with required non-authority statement.
- **`examples/reviewer-triage/*`** *(A, 11 files)* - ten decision examples plus a registry example.
- **`validators/creator_engine_validator/reviewer_triage.py`** *(A)* - offline ownership-only plan engine.
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* - `ce reviewer-triage plan` parser and dispatch.
- **`validators/tests/unit/test_reviewer_triage_plan.py`** *(A)* - TDD planner and CLI coverage.
- **`validators/tests/integration/test_reviewer_triage_examples.py`** *(A)* - schema validity for examples and non-authority enforcement.
- **`validators/tests/unit/test_v1_docs_reconciliation.py`** *(M)* - command inventory guard updated for the new `ce` group.
- **`docs/operations/REVIEWER_TRIAGE.md`** *(A)* - role-to-triage note, non-ratification boundary, and CODEOWNERS compatibility.
- **`specs/v2/adrs/ADR-V2-009-reviewer-venue-authority.md`** *(M)* - Phase-0 cross-pointer to ce-ops ADR-0003.
- **`README.md`** *(M)* - documents the new plan-only `ce reviewer-triage` command group.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* - rebuilt app wheel from this branch source.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - app-wheel digest re-pinned.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=25

AUTHORIZED_PATHS_SHA256=3d2c4e33a269273fc3d7c3b1a0c8cc7c8447020ecd441674929f390a5ef73994

```text
.ce/changelog/ce120-reviewer-triage.md
.ce/pr-manifests/ce120-reviewer-triage.md
README.md
docs/operations/REVIEWER_TRIAGE.md
examples/reviewer-triage/eligible.yaml
examples/reviewer-triage/missing-access.yaml
examples/reviewer-triage/no-available-reviewer.yaml
examples/reviewer-triage/privileged-requires-source.yaml
examples/reviewer-triage/reviewer-registry.yaml
examples/reviewer-triage/same-controller-tier1-reject.yaml
examples/reviewer-triage/same-host-tier2-valid.yaml
examples/reviewer-triage/same-human-reject.yaml
examples/reviewer-triage/tier4-release-valid.yaml
examples/reviewer-triage/uncontained-reject.yaml
examples/reviewer-triage/unresolved-identity-reject.yaml
schemas/reviewer-registry.schema.yaml
schemas/reviewer-triage-decision.schema.yaml
specs/v2/adrs/ADR-V2-009-reviewer-venue-authority.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/reviewer_triage.py
validators/tests/integration/test_reviewer_triage_examples.py
validators/tests/unit/test_reviewer_triage_plan.py
validators/tests/unit/test_v1_docs_reconciliation.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
