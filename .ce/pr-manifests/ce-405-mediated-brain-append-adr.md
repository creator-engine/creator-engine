# PR path manifest — ce-ops#405 · Propose a mediated append design for the hash-chained brain assertion ledger

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-405-mediated-brain-append-adr` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=09bb133f04e6e9c7c5fe7a619728b3ffb3d042c18157e8fd3633a5fa48f61b19

```text
.ce/changelog/ce-405-mediated-brain-append-adr.md
.ce/pr-manifests/ce-405-mediated-brain-append-adr.md
docs/adr/ADR-0005-mediated-brain-ledger-append.md
```
