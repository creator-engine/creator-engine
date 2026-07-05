# PR path manifest - ce-docs-pilot-welcome

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-docs-pilot-welcome` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=5146d0c42f097893be32e6594c918e4d6dd198f6e6073849ebabff8c40d2a6b3

```text
.ce/changelog/ce-docs-pilot-welcome.md
.ce/pr-manifests/ce-docs-pilot-welcome.md
docs/guide/welcome.md
```
