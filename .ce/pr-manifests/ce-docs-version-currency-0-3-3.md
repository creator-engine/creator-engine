# PR path manifest — ce-ops#467 · Docs version currency: bump current public docs to 0.3.3

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-docs-version-currency-0-3-3` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=30d121f43cd210b7226045d0c52af5de598f820f505ae2d6f389a54e3ac0ff34

```text
.ce/changelog/ce-docs-version-currency-0-3-3.md
.ce/pr-manifests/ce-docs-version-currency-0-3-3.md
README.md
docs/llms.txt
```
