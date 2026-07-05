# PR path manifest — ce-docs-brownfield-answers-version

- **Declared work class:** tiny

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref ce-docs-brownfield-answers-version`
and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=de975084256a3890e24de60ca81824f48490ee211debcb08cef7a54f86a01cff

```text
.ce/changelog/ce-docs-brownfield-answers-version.md
.ce/pr-manifests/ce-docs-brownfield-answers-version.md
docs/contracts/brownfield-adoption.md
```
