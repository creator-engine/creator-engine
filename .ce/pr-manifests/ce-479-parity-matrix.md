# PR path manifest — ticket 479 · harness parity-by-layer matrix

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-479-parity-matrix` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=16

AUTHORIZED_PATHS_SHA256=b44eb5321732d87665d3833400461993836dca45ae9ab0dc05a748595bda870d

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-479-parity-matrix.md
.ce/pr-manifests/ce-479-parity-matrix.md
.github/workflows/validate.yml
docs/operations/HARNESS_SUPPORT_CAPABILITY_MATRIX.md
validators/creator_engine_validator/checks/harness_promotion_matrix.py
validators/creator_engine_validator/cli.py
validators/creator_engine_validator/containment_status.py
validators/creator_engine_validator/harness_matrix.py
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_cli.py
validators/tests/unit/test_containment_status.py
validators/tests/unit/test_harness_matrix.py
validators/tests/unit/test_harness_promotion_matrix.py
validators/tests/unit/test_pr_preflight.py
validators/tests/unit/test_work_sizing_floor_ci_wiring.py
```
