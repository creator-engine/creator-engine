# PR path manifest — T4 CI migration: local gates

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref t4-ci-migration-local-gates` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** M

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=969d8a798d90ee13cf5a2ea12101d7719e0fe6d21e7b41d9556d49de2a21188b

```text
.ce/changelog/t4-ci-migration-local-gates.md
.ce/pr-manifests/t4-ci-migration-local-gates.md
.ce/reference/cli.generated.md
.github/workflows/validate.yml
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_ce_cli_preflight_gate.py
validators/tests/unit/test_pr_preflight.py
validators/tests/unit/test_t4_ci_migration_wiring.py
```
