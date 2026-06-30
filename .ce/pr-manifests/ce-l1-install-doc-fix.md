# PR path manifest — ce-ops#358 · Install spec: openssh-client prereq + 0.3.1 alignment, re-signed

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-l1-install-doc-fix` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=067eb6af18909c13f203010ece978161a8626259ebeb9894e0bc1a4e2b9ca9bb

```text
.ce/changelog/ce-l1-install-doc-fix.md
.ce/pr-manifests/ce-l1-install-doc-fix.md
docs/llms-install.md
```
