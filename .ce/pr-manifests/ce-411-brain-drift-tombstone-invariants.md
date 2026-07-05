# PR path manifest — creator-engine/ce-ops#411 · Brain drift tombstone invariants

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-411-brain-drift-tombstone-invariants` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=b74255b152ac7696bf1fd7228b60180210de16e5225fa1844d7a92bb9d21a998

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-411-brain-drift-tombstone-invariants.md
.ce/pr-manifests/ce-411-brain-drift-tombstone-invariants.md
validators/creator_engine_validator/checks/ce_brain_drift.py
validators/tests/unit/test_ce_brain_drift.py
```
