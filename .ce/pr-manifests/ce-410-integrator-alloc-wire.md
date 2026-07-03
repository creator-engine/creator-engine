# PR path manifest — ce-ops#410 · slice 3: integrator workspace allocation via daemon receipts

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-410-integrator-alloc-wire` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=1849b8d9d034681c5ba897cfb1c4be55d73e93a039cf5b1c865c400bf1a98662

```text
.ce/changelog/ce-410-integrator-alloc-wire.md
.ce/pr-manifests/ce-410-integrator-alloc-wire.md
validators/creator_engine_validator/forge/integrator_belt.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_integrator_belt.py
```
