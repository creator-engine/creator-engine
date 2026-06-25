# PR path manifest — ce-ops#177 · CE177 brain drift CI

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce177-brain-drift-ci` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=962fc9cbcda66a98e67d41d4be2b4b871f70a9e0af0e0b7c1d3e02f06c25fbbe

```text
.ce/changelog/ce177-brain-drift-ci.md
.ce/pr-manifests/ce177-brain-drift-ci.md
validators/creator_engine_validator/checks/ce_brain_drift.py
validators/tests/unit/test_ce_brain_drift.py
```
