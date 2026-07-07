# PR path manifest — ce-ops#477 · Slice D continuity drill harness

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-477-continuity-drill` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=13

AUTHORIZED_PATHS_SHA256=6700908c7999f346fa62bceeb919f15c61d69da2c530f530d33d824fe3bf0b1d

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-477-continuity-drill.md
.ce/pr-manifests/ce-477-continuity-drill.md
.ce/reference/cli.generated.md
README.md
docs/operations/SEAT_LAUNCH_GOVERNANCE_RUNBOOK.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/continuity_drill_runtime.py
validators/tests/unit/test_ce_brain_drift.py
validators/tests/unit/test_continuity_drill_cli.py
validators/tests/unit/test_v1_docs_reconciliation.py
validators/tests/unit/test_version_boundary.py
```
