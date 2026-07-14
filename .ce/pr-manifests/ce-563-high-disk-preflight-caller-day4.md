# PR path manifest — ce-ops#563 · High-disk preflight caller

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-563-high-disk-preflight-caller-day4` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=5d4f57bcb7d08d7d366fbf18a51b2dccdef75e468c0bc4a55ff23655a79a369e

```text
.ce/changelog/ce-563-high-disk-preflight-caller-day4.md
.ce/pr-manifests/ce-563-high-disk-preflight-caller-day4.md
validators/creator_engine_validator/high_disk_validation_consumer.py
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_disk_headroom.py
validators/tests/unit/test_high_disk_validation_consumer.py
```
