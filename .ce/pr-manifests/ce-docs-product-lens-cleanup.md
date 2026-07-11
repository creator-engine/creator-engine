# PR path manifest — Docs product-lens cleanup

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this documentation-only change. CI requires this PR's
base-to-head diff to equal exactly the paths below; this carrier lists itself.

Canonicalization: `sha256("\\n".join(sorted(unique_paths)) + "\\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=b71401a1f7ead00d863f45721442d599b71f275d2b1cd7504bc56aba7a1435ef

```text
.ce/changelog/ce-docs-product-lens-cleanup.md
.ce/pr-manifests/ce-docs-product-lens-cleanup.md
CHANGELOG.md
README.md
docs/guide/quickstart.md
docs/guide/solo-ceo-onboarding.md
docs/guide/welcome.md
docs/guide/zero-to-governed-seat-quickstart.md
```
