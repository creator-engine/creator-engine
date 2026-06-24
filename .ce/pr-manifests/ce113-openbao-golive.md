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

Per-file purpose (closed path-set - 23 paths):
- **`.ce/changelog/ce113-openbao-golive.md`** *(A)* - changelog fragment for go-live artifacts.
- **`.ce/pr-manifests/ce113-openbao-golive.md`** *(A)* - this closed carrier.
- **`docs/devops/openbao-operator-bringup.md`** *(A)* - Operator-only init/unseal/root-token/AppRole/secret-zero bringup runbook.
- **`docs/devops/openbao-production-golive.md`** *(A)* - production go-live operating runbook and held Operator actions.
- **`docs/devops/openbao/ce-dev-policy.hcl.tmpl`** *(A)* - per-dev least-privilege policy template with no cross-dev wildcard.
- **`docs/devops/openbao/emergency-revoke-openbao.sh`** *(A)* - per-dev lease/AppRole/emergency-seal revocation script.
- **`docs/devops/openbao/openbao.hcl.tmpl`** *(A)* - raft storage, tailnet-only TLS listener, and audit fail-closed HCL template.
- **`docs/devops/openbao/openbao.service`** *(A)* - hardened dedicated-user systemd unit.
- **`docs/devops/openbao/provision-openbao.sh`** *(A)* - idempotent plan/apply host provisioning script.
- **`docs/devops/openbao/render-dev-policy.sh`** *(A)* - safe renderer for per-dev policy files.
- **`docs/devops/openbao/restore-drill-openbao.sh`** *(A)* - encrypted snapshot restore-drill script for a throwaway instance.
- **`docs/devops/openbao/secret-migration-inventory.tsv`** *(A)* - value-free migration inventory template rows only; no live import values.
- **`docs/devops/openbao/snapshot-openbao.sh`** *(A)* - encrypted off-host raft snapshot script.
- **`docs/devops/openbao/verify-production-config-openbao-2.5.5.sh`** *(A)* - opt-in smoke that downloads/verifies OpenBao 2.5.5, loads the rendered production config, reloads it, and proves the file audit device activates.
- **`docs/devops/openbao/verify-secret-migration-inventory.sh`** *(A)* - value-free inventory gate that rejects duplicates and common secret-shaped material.
- **`validators/creator_engine_validator/openbao_golive.py`** *(A)* - value-free artifact validation helpers.
- **`validators/tests/integration/test_openbao_golive_production_config_live.py`** *(A)* - opt-in live regression for OpenBao 2.5.5 production config acceptance.
- **`validators/tests/integration/test_openbao_golive_restore_drill_live.py`** *(A)* - opt-in local OpenBao raft restore-drill proof.
- **`validators/tests/unit/test_openbao_golive.py`** *(A)* - unit coverage for artifacts and scripts.
- **`validators/tests/unit/test_openbao_p3.py`** *(M)* - parity coverage for OpenBao token-shaped migration evidence rejection.
- **`validators/tests/unit/test_secret_identity.py`** *(M)* - value-free placeholder coverage without embedding live-shaped literals.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - re-pinned app wheel digest only.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* - rebuilt app wheel containing `openbao_golive.py`.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=23

AUTHORIZED_PATHS_SHA256=fb703ef4b50954455271fb35dcf86ce94ec26494fc43ed18afd17c178273c66a

```text
.ce/changelog/ce113-openbao-golive.md
.ce/pr-manifests/ce113-openbao-golive.md
docs/devops/openbao-operator-bringup.md
docs/devops/openbao-production-golive.md
docs/devops/openbao/ce-dev-policy.hcl.tmpl
docs/devops/openbao/emergency-revoke-openbao.sh
docs/devops/openbao/openbao.hcl.tmpl
docs/devops/openbao/openbao.service
docs/devops/openbao/provision-openbao.sh
docs/devops/openbao/render-dev-policy.sh
docs/devops/openbao/restore-drill-openbao.sh
docs/devops/openbao/secret-migration-inventory.tsv
docs/devops/openbao/snapshot-openbao.sh
docs/devops/openbao/verify-production-config-openbao-2.5.5.sh
docs/devops/openbao/verify-secret-migration-inventory.sh
validators/creator_engine_validator/openbao_golive.py
validators/tests/integration/test_openbao_golive_production_config_live.py
validators/tests/integration/test_openbao_golive_restore_drill_live.py
validators/tests/unit/test_openbao_golive.py
validators/tests/unit/test_openbao_p3.py
validators/tests/unit/test_secret_identity.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
