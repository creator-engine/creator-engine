# PR path manifest — ce-ops#249 · public docs product-lens rewrite + ce-ops# CI guard

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce249-public-docs-product-lens` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=67004e47e533b4b351b08d59dd422e94212bebe960aa7d2ab820aa580f2f23b1

```text
.ce/changelog/ce249-public-docs-product-lens.md
.ce/pr-manifests/ce249-public-docs-product-lens.md
README.md
validators/tests/unit/test_public_docs_confidentiality.py
```
