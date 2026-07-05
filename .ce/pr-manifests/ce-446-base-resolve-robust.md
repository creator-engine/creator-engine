# PR path manifest — ce-ops#446 · robust moved-base comparison-base resolution in governance workflow

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-446-base-resolve-robust` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=6f8d434db1300f8597fa8f5a693fc98d6f0dfaa0d6e202bfc98c182e5de41477

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-446-base-resolve-robust.md
.ce/pr-manifests/ce-446-base-resolve-robust.md
.github/workflows/validate.yml
validators/tests/unit/test_ce_brain_drift.py
```
