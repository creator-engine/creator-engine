# PR path manifest — ce-ops#79 · Company Brain memory augmentation design

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-brain-memory-augmentation` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=956cd2a71464d333bcb124d2ac83ae609efb5baee070e1836be23efb263f69a4

```text
.ce/changelog/ce-brain-memory-augmentation.md
.ce/pr-manifests/ce-brain-memory-augmentation.md
docs/design/ce-brain-memory-augmentation.md
```
