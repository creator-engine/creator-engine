# PR path manifest -- ce-ops#235 dequeue + settle

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce235-dequeue-settle` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=7e94dd9c6e9cf46b6eec9a9c764c984fc157cba456249a6d08911ce75b8dee1f

```text
.ce/changelog/ce235-dequeue-settle.md
.ce/pr-manifests/ce235-dequeue-settle.md
README.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/forge/integrator_belt.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_integrator_belt.py
validators/tests/unit/test_v1_docs_reconciliation.py
```
