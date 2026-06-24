# PR path manifest — ce-ops#113 · OpenBao go-live + secret-migration dogfood automation

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs `verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref track-b-openbao-completion` and requires this PR's `origin/main..HEAD` diff to equal exactly the authorized path-set below (the carrier lists itself).

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=19

AUTHORIZED_PATHS_SHA256=255b76c0e8c7d04ff9fcb5846c27688d613832c7a4bb4e38e8f938b9ef115fc9

```text
.ce/changelog/ce113-openbao-golive.md
.ce/pr-manifests/track-b-openbao-completion.md
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
