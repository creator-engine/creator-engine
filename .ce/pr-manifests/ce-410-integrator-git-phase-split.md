# PR path manifest — ce-ops#410 · Split integrator git authority by phase

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-410-integrator-git-phase-split` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=50dc3350753c0c0109e26e9431d27cd9fe860e89a0438771af45efc22d442501

```text
.ce/changelog/ce-410-integrator-git-phase-split.md
.ce/pr-manifests/ce-410-integrator-git-phase-split.md
validators/creator_engine_validator/forge/integrator_belt.py
validators/tests/unit/test_integrator_belt.py
```
