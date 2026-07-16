# PR path manifest — ce-ops#536 · Canonicalize retired work classes in generated carriers

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-536-carrier-workclass-canonicalization` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=0962d89ac74edc8190a0a21ed72e40190dd7d50e9aa3d90abc35b12b968ea41b

```text
.ce/changelog/ce-536-carrier-workclass-canonicalization.md
.ce/pr-manifests/ce-536-carrier-workclass-canonicalization.md
validators/creator_engine_validator/carrier_gen.py
validators/tests/unit/test_carrier_gen.py
```
