# PR path manifest — Start Here guide and platform support matrix

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized
path-set for this PR. CI requires this branch's `base..HEAD` diff to equal exactly the
authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=2e8091de7a9099ce8440b49dd7f26d1465e5993453e291a6b9ea0ed850df9de2

```text
.ce/changelog/ce-docs-start-here-matrix.md
.ce/pr-manifests/ce-docs-start-here-matrix.md
docs/guide/start-here.md
docs/guide/support-matrix.md
```
