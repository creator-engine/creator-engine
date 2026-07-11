# PR path manifest — ce-docs-first-project · First-project tutorial

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI requires this branch's base-to-head diff to
equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=a45e6c0e4b33f665c4d5c774c184eb92bbfe8d26969b904856cde113aeabf60e

```text
.ce/changelog/ce-docs-first-project.md
.ce/pr-manifests/ce-docs-first-project.md
docs/guide/first-project.md
```
