# PR path manifest — ce-801-installer-envvar-docs

- **Declared work class:** tiny

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-801-installer-envvar-docs` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=96e0ee175e96c7d46eaf5aa5221b5f35552dae7b234dac2b07cfd45e1780a545

```text
.ce/changelog/ce-801-installer-envvar-docs.md
.ce/pr-manifests/ce-801-installer-envvar-docs.md
docs/contracts/installer.md
```
