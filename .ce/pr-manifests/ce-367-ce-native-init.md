# PR path manifest — ce-ops#367 · CE-native ce init project scaffolding

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-367-ce-native-init` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** M

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=13

AUTHORIZED_PATHS_SHA256=aeda66bebae8a10ac00d6da1bbef8b783b2467f06569dc8ceee29cc9e1536f4c

```text
.ce/changelog/ce-367-ce-native-init.md
.ce/pr-manifests/ce-367-ce-native-init.md
.ce/reference/cli.generated.md
README.md
scripts/gen_cli_reference.py
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/project_init.py
validators/tests/integration/test_ce_init_cli.py
validators/tests/unit/test_ce_init_cli.py
validators/tests/unit/test_project_init.py
validators/tests/unit/test_v1_docs_reconciliation.py
validators/tests/unit/test_version_boundary.py
```
