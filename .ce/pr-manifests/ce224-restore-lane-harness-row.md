# PR path manifest - ce224-restore-lane-harness-row

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs `verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce224-restore-lane-harness-row` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below. This carrier lists itself.

Scope:
ce-ops#224 restores the `lane` harness row to the probed harness-support matrix, deriving Ring 1 from the real lane hook invariant instead of a hardcoded capability.

Per-file purpose:
- **`.ce/changelog/ce224-restore-lane-harness-row.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce224-restore-lane-harness-row.md`** *(A)* - this closed path-set carrier.
- **`docs/operations/HARNESS_SUPPORT_CAPABILITY_MATRIX.md`** *(M)* - regenerated rendered matrix doc with restored `lane` row.
- **`validators/creator_engine_validator/harness_matrix.py`** *(M)* - restore `lane` row and `_lane_ring1_probe`-derived capability cells.
- **`validators/tests/unit/test_containment_status.py`** *(M)* - assert default containment-status fleet includes `lane`.
- **`validators/tests/unit/test_harness_matrix.py`** *(M)* - pin `lane` as a required harness and verify its probed Ring 1 provenance.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=254fe8bcb9fcb7d17128c5388f7d1f6c4ca19053447ade68dff08eaa04229863

```text
.ce/changelog/ce224-restore-lane-harness-row.md
.ce/pr-manifests/ce224-restore-lane-harness-row.md
docs/operations/HARNESS_SUPPORT_CAPABILITY_MATRIX.md
validators/creator_engine_validator/harness_matrix.py
validators/tests/unit/test_containment_status.py
validators/tests/unit/test_harness_matrix.py
```
