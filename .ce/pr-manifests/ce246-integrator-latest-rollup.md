# PR path manifest - ce-ops#246 - integrator latest required rollup checks

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce246-integrator-latest-rollup` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=8563868c677fd37f033ce01a005675a20a62ebdaa6389acf9016222810493118

```text
.ce/changelog/ce246-integrator-latest-rollup.md
.ce/pr-manifests/ce246-integrator-latest-rollup.md
validators/creator_engine_validator/forge/integrator_belt.py
validators/tests/unit/test_integrator_belt.py
```
