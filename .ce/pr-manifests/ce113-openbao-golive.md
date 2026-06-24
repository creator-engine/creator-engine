# PR path manifest - ce113-openbao-golive - OpenBao production go-live

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce113-openbao-golive
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The carrier lists itself.

Scope:
Build deployable and tested ce-ops#113 production go-live artifacts for the
Operator-ratified Hetzner VPS, logically segregated and tailnet-only OpenBao
topology. This PR does not initialize or unseal production, does not inject real
secret-zero, and does not migrate live secrets.

Per-file purpose (closed path-set - 19 paths):
- **`.ce/changelog/ce113-openbao-golive.md`** *(A)* - changelog fragment for go-live artifacts.
- **`.ce/pr-manifests/ce113-openbao-golive.md`** *(A)* - this closed carrier.
- **`docs/devops/openbao-operator-bringup.md`** *(A)* - Operator-only init/unseal/root-token/AppRole/secret-zero bringup runbook.
- **`docs/devops/openbao-production-golive.md`** *(A)* - production go-live operating runbook and held Operator actions.
- **`docs/devops/openbao/bringup-container-openbao.sh`** *(A)* - dry-run-first single-node container bring-up for synthetic dogfood and live-test prep.
- **`docs/devops/openbao/ce-broker-policy.hcl.tmpl`** *(A)* - value-free broker policy template for wrapped AppRole SecretID issuance.
- **`docs/devops/openbao/ce-operator-import-policy.hcl.tmpl`** *(A)* - short-lived Operator-only import policy template for ratified migration windows.
- **`docs/devops/openbao/openbao-secret-path-map.tsv`** *(A)* - name-only map for per-dev PATs, Claude OAuth, GitHub App config/key families, reviewer app names, and deferred `ce-root-v1`.
- **`docs/devops/openbao/secret-migration-inventory.tsv`** *(A)* - value-free migration inventory template rows only; no live import values.
- **`docs/devops/openbao/verify-secret-migration-inventory.sh`** *(A)* - value-free inventory gate that rejects duplicates and common secret-shaped material.
- **`validators/creator_engine_validator/openbao_golive.py`** *(A)* - value-free artifact validation helpers.
- **`validators/creator_engine_validator/openbao_p3.py`** *(M)* - OpenBao phase-3 validator helper updates already in this branch.
- **`validators/creator_engine_validator/secret_identity.py`** *(M)* - SecretIdentity OpenBao placeholder handling already in this branch.
- **`validators/tests/integration/test_openbao_golive_production_config_live.py`** *(A)* - opt-in live regression for OpenBao 2.5.5 production config acceptance.
- **`validators/tests/integration/test_openbao_golive_restore_drill_live.py`** *(A)* - opt-in local OpenBao raft restore-drill proof.
- **`validators/tests/unit/test_openbao_container_golive.py`** *(A)* - unit coverage for the canonical container bring-up script and path map.
- **`validators/tests/unit/test_openbao_golive.py`** *(A)* - unit coverage for artifacts and scripts.
- **`validators/tests/unit/test_openbao_p3.py`** *(M)* - parity coverage for OpenBao token-shaped migration evidence rejection.
- **`validators/tests/unit/test_secret_identity.py`** *(M)* - value-free placeholder coverage without embedding live-shaped literals.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=19

AUTHORIZED_PATHS_SHA256=5c970662590485a173eaf215fe70be599e584dc92c493ae8a359b56d9b8f5462

```text
.ce/changelog/ce113-openbao-golive.md
.ce/pr-manifests/ce113-openbao-golive.md
docs/devops/openbao-operator-bringup.md
docs/devops/openbao-production-golive.md
docs/devops/openbao/bringup-container-openbao.sh
docs/devops/openbao/ce-broker-policy.hcl.tmpl
docs/devops/openbao/ce-operator-import-policy.hcl.tmpl
docs/devops/openbao/openbao-secret-path-map.tsv
docs/devops/openbao/secret-migration-inventory.tsv
docs/devops/openbao/verify-secret-migration-inventory.sh
validators/creator_engine_validator/openbao_golive.py
validators/creator_engine_validator/openbao_p3.py
validators/creator_engine_validator/secret_identity.py
validators/tests/integration/test_openbao_golive_production_config_live.py
validators/tests/integration/test_openbao_golive_restore_drill_live.py
validators/tests/unit/test_openbao_container_golive.py
validators/tests/unit/test_openbao_golive.py
validators/tests/unit/test_openbao_p3.py
validators/tests/unit/test_secret_identity.py
```
