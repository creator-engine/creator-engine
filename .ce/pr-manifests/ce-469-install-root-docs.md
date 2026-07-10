# PR path manifest - ce-469-install-root-docs

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-469-install-root-docs` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** XS

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=4e5fe615b67b1d215c669f6bf0d4704d071aa6bf53764dbf618e2714ff248649

```text
.ce/changelog/ce-469-install-root-docs.md
.ce/pr-manifests/ce-469-install-root-docs.md
docs/contracts/installer.md
docs/reference/cli.md
```
