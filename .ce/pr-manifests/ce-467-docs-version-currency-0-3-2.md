# PR path manifest — ce-ops#467 · Docs version currency: bump stale 0.3.0 references to 0.3.2

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-467-docs-version-currency-0-3-2` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=027fa873431d239d736c413709cb5b27532f07bcaac4e26d84e7e83f668c9104

```text
.ce/changelog/ce-467-docs-version-currency-0-3-2.md
.ce/pr-manifests/ce-467-docs-version-currency-0-3-2.md
README.md
```
