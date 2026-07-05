# PR path manifest — ce-ops#455 · Tenant-lens brownfield onboard refusals

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-455-refusal-message-tenant-lens` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=041ea4aa6e4c5ce53bbfd978e826bfe51170210c350f702652d3f79e952acb07

```text
.ce/changelog/ce-455-refusal-message-tenant-lens.md
.ce/pr-manifests/ce-455-refusal-message-tenant-lens.md
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_v3_brownfield_refusals.py
validators/tests/unit/test_v3_cli.py
```
