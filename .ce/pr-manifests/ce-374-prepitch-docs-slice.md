# PR path manifest — ce-374-prepitch-docs-slice · Rendered Creator Engine overview docs page

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-374-prepitch-docs-slice` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** `story`

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=9172061ccf9c401aebe1fdd3631ac2e0a4f54145a4303c95cc6ea6506ee25236

```text
.ce/changelog/ce-374-prepitch-docs-slice.md
.ce/pr-manifests/ce-374-prepitch-docs-slice.md
docs/index.html
docs/what-is-creator-engine.html
validators/tests/unit/test_site_index_docs_nav.py
```
