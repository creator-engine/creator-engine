# PR path manifest — ce-ops#378 · canary: dev-3 contained self-push spine

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-canary-dev3-selfpush` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=2

AUTHORIZED_PATHS_SHA256=e4e1f7c0e18bdff32d20eb528a734445ef82d7238011216d2621ecbaabd80d45

```text
.ce/changelog/ce-canary-dev3-selfpush.md
.ce/pr-manifests/ce-canary-dev3-selfpush.md
```
