# PR path manifest — T4 CI migration: local gates

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref t4-ci-migration-local-gates` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** M

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=efd5422f8563231d7f5b7eab1ba45e1a245546ab0ed69002f6e38a3a08ca7585

```text
.ce/changelog/t4-ci-migration-local-gates.md
.ce/pr-manifests/t4-ci-migration-local-gates.md
.github/workflows/validate.yml
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_ce_cli_preflight_gate.py
validators/tests/unit/test_pr_preflight.py
validators/tests/unit/test_t4_ci_migration_wiring.py
```
