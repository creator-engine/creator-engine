# PR path manifest - ce113-openbao-design - OpenBao SecretIdentityBackend Phase 0-2

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce113-openbao-design
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. The carrier lists itself.

Ratified gate:
Controller Wave 2 APPROVE-WITH-NITS on 2026-06-19 for ce-ops#113. Build
Phase 0/1/2 only: accepted ADR-0005, design hard-gate addenda B.1-B.5,
SecretIdentityBackend interface substrate, fake backend, schemas, and CI-pure
OpenBao adapter. No push. No live OpenBao deployment, migration, unseal,
backup, or secret import. B.6 migration is held.

PR #265 CI fix:
Rebuilt the app wheel so `validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`
contains `creator_engine_validator/secret_identity.py`, and re-pinned
`validators/wheelhouse/SHA256SUMS`.

Per-file purpose (closed path-set - 10 paths):
- **`.ce/pr-manifests/ce113-openbao-design.md`** *(A)* - this carrier.
- **`.ce/changelog/ce113-openbao-design.md`** *(A)* - changelog fragment.
- **`.ce/state/research/DESIGN_ce113_openbao_20260619T031542Z.md`** *(A)* - Phase 0 design with controller B.1-B.5 hard-gate addenda; B.6 held.
- **`docs/decisions/0005-openbao-secret-identity-backend.md`** *(A)* - Operator-accepted ADR-0005 decision record.
- **`schemas/secret-ref.schema.yaml`** *(A)* - value-free logical secret reference schema.
- **`schemas/secret-grant.schema.yaml`** *(A)* - value-free secret grant schema.
- **`validators/creator_engine_validator/secret_identity.py`** *(A)* - SecretIdentityBackend protocol, registry, fake backend, and injected-I/O OpenBao adapter.
- **`validators/tests/unit/test_secret_identity.py`** *(A)* - strict TDD coverage for Phase 1/2 contracts.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* - rebuilt app wheel containing `secret_identity.py`.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - re-pinned app wheel digest.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=31567770e3078f01200b1535c4f65c6ebe3dcfa6fc2a859bf46464b65cedabef

```text
.ce/changelog/ce113-openbao-design.md
.ce/pr-manifests/ce113-openbao-design.md
.ce/state/research/DESIGN_ce113_openbao_20260619T031542Z.md
docs/decisions/0005-openbao-secret-identity-backend.md
schemas/secret-grant.schema.yaml
schemas/secret-ref.schema.yaml
validators/creator_engine_validator/secret_identity.py
validators/tests/unit/test_secret_identity.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
