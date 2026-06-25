# PR path manifest — ce-ops#177 · Structured brain-drift findings

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce177-drift-findings` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=ea1f64354f293dbd9909c6edb13f740f6cc38c57b82e60efe934cd7199e864b0

```text
.ce/changelog/ce177-drift-findings.md
.ce/pr-manifests/ce177-drift-findings.md
validators/creator_engine_validator/checks/ce_brain_drift.py
validators/tests/unit/test_ce_brain_drift.py
```
