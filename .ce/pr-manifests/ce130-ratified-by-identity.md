# PR path manifest - ce130-ratified-by-identity

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce130-ratified-by-identity
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Scope:
ce-ops#130 bounded decision-record fix. Accepted Decision Records must record
the actual ratifier handle in `ratification.ratified_by`, not generic role
placeholders such as `the Operator`. This change updates the validator invariant,
contract/schema wording, existing ADR-0005 metadata, unit coverage, and the
rebuilt validator app wheel. No served trust-root paths are touched.

Base:
`d2d22b0` (`origin/main` at rebase, post PR #276).

Per-file purpose (closed path-set - 9 paths):
- **`.ce/changelog/ce130-ratified-by-identity.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce130-ratified-by-identity.md`** *(A)* - this carrier.
- **`docs/contracts/decision-record.md`** *(M)* - contract text for concrete ratifier handles.
- **`docs/decisions/0005-openbao-secret-identity-backend.md`** *(M)* - replace generic ratifier placeholder with the actual handle.
- **`schemas/decision-record.schema.yaml`** *(M)* - schema description for `ratified_by`.
- **`validators/creator_engine_validator/checks/decision_record.py`** *(M)* - concrete-ratifier invariant.
- **`validators/tests/unit/test_decision_record.py`** *(M)* - regression coverage.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - app wheel digest refresh only.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* - rebuilt app wheel containing the validator change.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=1549b9c3d25916a56eca4232d5ef1d2d5a3e4b5d2fc2ccc1b294aa30d2606a6a

```text
.ce/changelog/ce130-ratified-by-identity.md
.ce/pr-manifests/ce130-ratified-by-identity.md
docs/contracts/decision-record.md
docs/decisions/0005-openbao-secret-identity-backend.md
schemas/decision-record.schema.yaml
validators/creator_engine_validator/checks/decision_record.py
validators/tests/unit/test_decision_record.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
