# PR path manifest — creator-engine/ce-ops#454 · Merge-triggered dependency-unlock executor, SHADOW-first (slice 1)

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-454-dependency-unlock-executor` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** epic

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=d5aebb501fb38c6eb91ee5e6cb80f61519064626d47b9715bc2431d953189760

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-454-dependency-unlock-executor.md
.ce/pr-manifests/ce-454-dependency-unlock-executor.md
.github/workflows/ce-dependency-unlock.yml
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/dependency_unlock.py
validators/tests/unit/test_ce_brain_drift.py
validators/tests/unit/test_dependency_unlock.py
validators/tests/unit/test_v1_docs_reconciliation.py
```
