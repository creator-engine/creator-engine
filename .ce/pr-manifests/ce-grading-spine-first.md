# PR path manifest - ce-grading-spine-first

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-grading-spine-first --require-carrier
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

- **Declared work class:** feature

Scope:
Spine-first grading additive-safety slice. This adds deterministic spine
verdict primitives, mode/tier independence policy selection, review-evidence
independence attestations, and approval-capability policy digest binding. It
does not enable autonomous merge, deploy, broker behavior, branch protection
mutation, launcher changes, or privileged actuation.

Per-file purpose:
- **`.ce/changelog/ce-grading-spine-first.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce-grading-spine-first.md`** *(A)* - this closed path-set carrier.
- **`docs/contracts/grading-spine.md`** *(A)* - spine-first grading contract.
- **`docs/contracts/review-evidence.md`** *(M)* - documents independence attestation fields.
- **`docs/delivery/REVIEW_EVIDENCE_TEMPLATE.md`** *(M)* - keeps the prose review-evidence template aligned with the attestation fields.
- **`examples/malformed/review-evidence/invalid-verdict-value.yml`** *(M)* - keeps malformed fixture schema-complete for new required fields.
- **`examples/malformed/review-evidence/missing-non-ratification-statement.yml`** *(M)* - keeps malformed fixture schema-complete for new required fields.
- **`examples/malformed/review-evidence/missing-verdict.yml`** *(M)* - keeps malformed fixture schema-complete for new required fields.
- **`examples/well-formed/review-evidence/example-review-evidence.yml`** *(M)* - adds well-formed attestation fields.
- **`schemas/review-evidence.schema.yaml`** *(M)* - adds required independence attestation fields.
- **`templates/review-evidence.template.yaml`** *(M)* - adds template placeholders for attestation fields.
- **`validators/creator_engine_validator/forge/approval_capability.py`** *(M)* - exposes mode/tier-bound approval policy digest derivation.
- **`validators/creator_engine_validator/grading_policy.py`** *(A)* - data-only mode/tier independence policy helpers.
- **`validators/creator_engine_validator/grading_spine.py`** *(A)* - deterministic spine verdict helpers.
- **`validators/tests/unit/test_approval_capability_policy_binding.py`** *(A)* - covers replay rejection across mode/tier policy digests.
- **`validators/tests/unit/test_grading_policy.py`** *(A)* - covers policy selection and review-evidence independence checks.
- **`validators/tests/unit/test_grading_spine.py`** *(A)* - covers green/red spine and semantic grade counting.
- **`validators/tests/unit/test_review_evidence_schema.py`** *(M)* - updates valid fixture for required attestation fields.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=18

AUTHORIZED_PATHS_SHA256=83334a39ca33bf3d08eeaf6628a50cbf8a6e51f8c95cd74218f437c7e139a19e

```text
.ce/changelog/ce-grading-spine-first.md
.ce/pr-manifests/ce-grading-spine-first.md
docs/contracts/grading-spine.md
docs/contracts/review-evidence.md
docs/delivery/REVIEW_EVIDENCE_TEMPLATE.md
examples/malformed/review-evidence/invalid-verdict-value.yml
examples/malformed/review-evidence/missing-non-ratification-statement.yml
examples/malformed/review-evidence/missing-verdict.yml
examples/well-formed/review-evidence/example-review-evidence.yml
schemas/review-evidence.schema.yaml
templates/review-evidence.template.yaml
validators/creator_engine_validator/forge/approval_capability.py
validators/creator_engine_validator/grading_policy.py
validators/creator_engine_validator/grading_spine.py
validators/tests/unit/test_approval_capability_policy_binding.py
validators/tests/unit/test_grading_policy.py
validators/tests/unit/test_grading_spine.py
validators/tests/unit/test_review_evidence_schema.py
```
