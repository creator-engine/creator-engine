# PR path manifest — ce-ops#34 · Design CE forge-side automation layer

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-34-forge-design` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=39a8f8d780af3b5cc2b84def89bd7d2a42504dabbbe3c8b9c4e6f10de2f80633

- **Declared work class:** story

```text
.ce/changelog/ce-34-forge-design.md
.ce/pr-manifests/ce-34-forge-design.md
docs/design/ce-forge-side-automation-epic.md
docs/design/ce-forge-side-automation.md
```
