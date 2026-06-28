# PR path manifest — ce-ops#348 · ratify + promote ADR-0013 (substrate-independent authority)

- **Declared work class:** story

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-348-adr-0013-promote` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=4e30c8006e5bfd3874176733780633c3209ce0e36a982037e4b68ad9cad68c40

```text
.ce/changelog/ce-348-adr-0013-promote.md
.ce/pr-manifests/ce-348-adr-0013-promote.md
docs/decisions/ADR-0013-substrate-independent-authority.md
```
