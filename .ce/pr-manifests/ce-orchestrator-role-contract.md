# PR path manifest — ce-ops#616 · Orchestrator role contract

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-orchestrator-role-contract` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=e6c1797e568ac063ed0a040ac5d22b719ccc72e96dcb426a260ae9874d1f5e70

```text
.ce/changelog/ce-orchestrator-role-contract.md
.ce/pr-manifests/ce-orchestrator-role-contract.md
docs/contracts/orchestrator.md
```
