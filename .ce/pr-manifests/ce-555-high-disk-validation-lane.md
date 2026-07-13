# PR path manifest — ce-ops#555 · High-disk validation lane adapter

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-555-high-disk-validation-lane` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=09559d7c727a75f5a246c7cb1b5b3e93b093a764558da024b5cf5d26617dec45

```text
.ce/changelog/ce-555-high-disk-validation-lane.md
.ce/pr-manifests/ce-555-high-disk-validation-lane.md
validators/creator_engine_validator/high_disk_validation_lane.py
validators/tests/unit/test_high_disk_validation_lane.py
```
