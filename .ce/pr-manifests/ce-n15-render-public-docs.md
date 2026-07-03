# PR path manifest — N1.5 · Render public docs to HTML

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-n15-render-public-docs` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** XS

AUTHORIZED_PATHS_COUNT=2

AUTHORIZED_PATHS_SHA256=9430351e65fec3887a41b6f146437195bd3b465c291579fe946c632fa564fe55

```text
.ce/changelog/ce-n15-render-public-docs.md
.ce/pr-manifests/ce-n15-render-public-docs.md
```
