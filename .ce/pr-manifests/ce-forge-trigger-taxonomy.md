# PR path manifest — FORGE-2 · Define forge trigger taxonomy

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-forge-trigger-taxonomy` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=793a418e4bf1d60618eff82cf59b74c9099559f869639f1af7abcc9199190c4e

- **Declared work class:** story

```text
.ce/changelog/ce-forge-trigger-taxonomy.md
.ce/pr-manifests/ce-forge-trigger-taxonomy.md
docs/contracts/forge-trigger-taxonomy.md
```
