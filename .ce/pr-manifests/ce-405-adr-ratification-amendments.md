# PR path manifest — ce-ops#405 · Ratify ADR-0005 with three ratification-time amendments

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-405-adr-ratification-amendments` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=0a0acd2f2c837992036c67f67d714bbfc4561b78595a1ff0f15026f85926e693

```text
.ce/changelog/ce-405-adr-ratification-amendments.md
.ce/pr-manifests/ce-405-adr-ratification-amendments.md
docs/adr/ADR-0005-mediated-brain-ledger-append.md
```
