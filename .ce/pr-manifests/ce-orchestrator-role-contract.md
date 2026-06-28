# PR path manifest — ce-ops#616 · Orchestrator role contract

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-orchestrator-role-contract` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=22607ffd53b8cae83a3927dc8fbf8094e7204bd46e9a6e64c73a14a416b550a7

```text
.ce/changelog/ce-orchestrator-role-contract.md
.ce/pr-manifests/ce-orchestrator-role-contract.md
docs/contracts/orchestrator.md
validators/creator_engine_validator/public_docs_confidentiality.py
```
