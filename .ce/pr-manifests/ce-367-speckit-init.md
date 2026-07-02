# PR path manifest — ce-ops#367 · Add ce speckit init scaffold

- **Declared work class:** feature

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-367-speckit-init` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=8e5861f992ce1cfe13794b9e9ca7180e1f94a71975c03ec471b0fae74cdd82c2

```text
.ce/changelog/ce-367-speckit-init.md
.ce/pr-manifests/ce-367-speckit-init.md
.ce/reference/cli.generated.md
README.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/speckit_init.py
validators/tests/unit/test_speckit_init.py
validators/tests/unit/test_v1_docs_reconciliation.py
```
