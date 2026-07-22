# PR path manifest — ce-ops#638 · Reframe carrier-slug derivation guidance

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce638-slug-derivation-guidance` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=6b8500b8f4114a741473e0d6cd398ccc8f4ddcddfdb9533fd742a90f3411a8cc

```text
.ce/brain/assertions.yaml
.ce/changelog/ce638-slug-derivation-guidance.md
.ce/pr-manifests/ce638-slug-derivation-guidance.md
docs/contracts/authoring-a-governed-pr.md
docs/operations/AUTHOR_A_CE_VALID_PR.md
```
