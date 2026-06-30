# PR path manifest — ce-ops#0 · Harden release workflow GitHub expression injection boundaries

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-l7-injection-cleanup` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** tiny

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=1a7801bc0e771847b2f91b708629dc15cc16e1ac7c5c866ab4e08819f6c8b97d

```text
.ce/changelog/ce-l7-injection-cleanup.md
.ce/pr-manifests/ce-l7-injection-cleanup.md
.github/workflows/release-finalize.yml
.github/workflows/release.yml
```
