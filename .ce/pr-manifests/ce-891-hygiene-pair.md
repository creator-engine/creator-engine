# PR path manifest — ce-ops#891 · DGX runsc hygiene tests and docs

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-891-hygiene-pair` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** XS

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=a456eb668cb9e97d7aacfcfdbf7af7682ae0e0abb01c93b76e48f15e659771fa

```text
.ce/changelog/ce-891-hygiene-pair.md
.ce/pr-manifests/ce-891-hygiene-pair.md
deploy/dgx-runsc/README.md
deploy/dgx-runsc/test-seat-logging.sh
```
