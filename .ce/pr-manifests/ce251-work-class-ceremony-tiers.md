# PR path manifest — ce-ops#251 · Reframe work classes as CE ceremony tiers

- **Declared work class:** tiny

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce251-work-class-ceremony-tiers` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=0736ae03102049a5f8cc441e27238bacfbcb8ac91dec92a85c8f377cf59d6bb2

```text
.ce/changelog/ce251-work-class-ceremony-tiers.md
.ce/pr-manifests/ce251-work-class-ceremony-tiers.md
docs/contracts/work-sizing-tiers.md
docs/operations/AUTHOR_A_CE_VALID_PR.md
```
