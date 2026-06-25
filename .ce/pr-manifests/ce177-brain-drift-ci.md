# PR path manifest — ce-ops#177 · Structured brain-drift findings

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce177-brain-drift-ci` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=468a56154d176d4f673f8f68d572f3f2a92c6b06fce096f88530177503709883

```text
.ce/changelog/ce177-brain-drift-findings.md
.ce/pr-manifests/ce177-brain-drift-ci.md
validators/creator_engine_validator/checks/ce_brain_drift.py
validators/tests/unit/test_ce_brain_drift.py
```
