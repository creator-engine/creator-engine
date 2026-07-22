# PR path manifest — T4 CI migration: local gates

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref t4-ci-migration-local-gates` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** M

AUTHORIZED_PATHS_COUNT=13

AUTHORIZED_PATHS_SHA256=6efacd2672501dc33b64b00368f0585df62f1ab5560c0014c338b257996aa676

```text
.ce/brain/assertions.yaml
.ce/changelog/t4-ci-migration-local-gates.md
.ce/pr-manifests/t4-ci-migration-local-gates.md
.ce/reference/cli.generated.md
.github/workflows/validate.yml
README.md
docs/reference/cli.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_ce_cli_preflight_gate.py
validators/tests/unit/test_pr_preflight.py
validators/tests/unit/test_t4_ci_migration_wiring.py
validators/tests/unit/test_v1_docs_reconciliation.py
```
