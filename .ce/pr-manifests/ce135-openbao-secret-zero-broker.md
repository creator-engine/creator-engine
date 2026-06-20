# PR path manifest - ce135-openbao-secret-zero-broker - OpenBao secret-zero broker

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce135-openbao-secret-zero-broker
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The carrier lists itself.

Scope:
Design and implement the ce-ops#135 OpenBao broker / secret-zero wiring behind
the `SecretIdentityBackend` seam. This PR adds value-free broker minting of
short-TTL response-wrapped per-dev AppRole SecretIDs plus seat-side unwrap/login
helpers for dev tokens. It does not execute production init, unseal, root-token,
real SecretID, PEM import, or live secret migration actions.

Per-file purpose (closed path-set - 12 paths):
- **`.ce/changelog/ce135-openbao-secret-zero-broker.md`** *(A)* - changelog fragment for the broker wiring.
- **`.ce/pr-manifests/ce135-openbao-secret-zero-broker.md`** *(A)* - this closed carrier.
- **`.ce/state/research/DESIGN_ce135_openbao_secret_zero_broker_20260620.md`** *(A)* - security-sensitive design-first artifact.
- **`docs/contracts/openbao-secret-zero-broker.md`** *(A)* - value-free broker/seat secret-zero contract.
- **`docs/devops/openbao-operator-bringup.md`** *(M)* - operator runbook updated to distinguish brokered steady-state from manual break-glass minting.
- **`schemas/secret-zero-grant.schema.yaml`** *(A)* - schema for value-free `SecretZeroGrant` records.
- **`validators/creator_engine_validator/openbao_p3.py`** *(M)* - injected HTTP runner emits OpenBao wrap TTL header.
- **`validators/creator_engine_validator/secret_identity.py`** *(M)* - `SecretIdentityBackend` secret-zero request/grant/session objects and OpenBao broker/seat implementation.
- **`validators/tests/unit/test_openbao_p3.py`** *(M)* - wrap TTL header regression.
- **`validators/tests/unit/test_secret_identity.py`** *(M)* - broker issue, seat redeem, redaction, and schema tests.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - re-pinned app wheel digest only.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* - rebuilt app wheel containing the adapter changes.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=12

AUTHORIZED_PATHS_SHA256=af54fc2c7c87bf06dbc6e36836ec97079c0e468310e3fb1b99ff7c51a8121714

```text
.ce/changelog/ce135-openbao-secret-zero-broker.md
.ce/pr-manifests/ce135-openbao-secret-zero-broker.md
.ce/state/research/DESIGN_ce135_openbao_secret_zero_broker_20260620.md
docs/contracts/openbao-secret-zero-broker.md
docs/devops/openbao-operator-bringup.md
schemas/secret-zero-grant.schema.yaml
validators/creator_engine_validator/openbao_p3.py
validators/creator_engine_validator/secret_identity.py
validators/tests/unit/test_openbao_p3.py
validators/tests/unit/test_secret_identity.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
