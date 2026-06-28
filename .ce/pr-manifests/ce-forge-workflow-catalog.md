# PR path manifest — ce-ops#34 · Workflow-as-artifact catalog

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-forge-workflow-catalog` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=6d16393593d6a4c46a0a8d7b9f524f74b15dea914a187ffd5aaad6d7ff35fbc7

```text
.ce/changelog/ce-forge-workflow-catalog.md
.ce/pr-manifests/ce-forge-workflow-catalog.md
docs/contracts/workflow-catalog.md
```
