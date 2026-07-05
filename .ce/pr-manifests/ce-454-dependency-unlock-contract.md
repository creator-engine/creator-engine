# PR path manifest — ce-454 · Dependency unlock contract

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-454-dependency-unlock-contract` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=ee5299f06edea088d708e62c23fc73f0a5fb723dd50b5c89d4c8d617584dcf59

```text
.ce/brain/doctrine-coverage.yaml
.ce/changelog/ce-454-dependency-unlock-contract.md
.ce/pr-manifests/ce-454-dependency-unlock-contract.md
docs/contracts/dependency-unlock.md
```
