# PR path manifest — ce-ops#34 · Add ratification-gated workflow registry

- **Declared work class:** story

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-forge-workflow-registry` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=0df6b14c2483f9aa5946b7f5ac3f4810460c6c0e976eaf6cac411a43c8bfcf54

```text
.ce/changelog/ce-forge-workflow-registry.md
.ce/pr-manifests/ce-forge-workflow-registry.md
validators/creator_engine_validator/forge/workflow_registry.py
validators/tests/unit/test_workflow_registry.py
```
