# PR path manifest — creator-engine/ce-ops#440 · docs: align dogfood-migration systemd snippets with the unified ce surface

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-440-s3c-migration-doc-snippets` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=c6fdd9d28dce6c85ee3669ab0cf50105cb77139f6b4582fdbe0c96c077b27ff5

```text
.ce/changelog/ce-440-s3c-migration-doc-snippets.md
.ce/pr-manifests/ce-440-s3c-migration-doc-snippets.md
docs/operations/INSTALLED_CE_DOGFOOD_MIGRATION.md
```
