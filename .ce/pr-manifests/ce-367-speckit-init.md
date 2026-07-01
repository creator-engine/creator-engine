# PR path manifest — ce-ops#367 · Add ce speckit init scaffold

- **Declared work class:** M

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-367-speckit-init` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=007ff039e21bbcec2eb4e51cc64d608904967e8ebc1ce9e9c899c28cd323aade

```text
.ce/changelog/ce-367-speckit-init.md
.ce/pr-manifests/ce-367-speckit-init.md
README.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/speckit_init.py
validators/tests/unit/test_speckit_init.py
validators/tests/unit/test_v1_docs_reconciliation.py
```
