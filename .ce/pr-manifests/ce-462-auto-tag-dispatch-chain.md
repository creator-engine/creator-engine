# PR path manifest — ce-ops#462 · fix: release-auto-tag explicit ordered dispatch (GITHUB_TOKEN suppression)

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-462-auto-tag-dispatch-chain` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=9dc66a486c066b2c8c40093eeffe159f7ff19569698b589b4d5ead48ea1edf68

```text
.ce/changelog/ce-462-auto-tag-dispatch-chain.md
.ce/pr-manifests/ce-462-auto-tag-dispatch-chain.md
.github/workflows/release-auto-tag.yml
```
