# PR path manifest — ce-ops#34 · Forge persona catalog

- **Declared work class:** story

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-forge-persona-catalog` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=f4f1ad4dbd0d248b15a8dcd8ece9fc8034674c9ba4346f1adbda68134482ce77

```text
.ce/changelog/ce-forge-persona-catalog.md
.ce/pr-manifests/ce-forge-persona-catalog.md
docs/contracts/forge-persona-catalog.md
```
