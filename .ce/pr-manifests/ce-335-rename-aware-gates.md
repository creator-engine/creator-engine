# PR path manifest — ce-ops#335 · rename-aware validator gates

- **Declared work class:** story

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-335-rename-aware-gates

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified:
ce-ops#335 fixes rename-blind PR diff accounting in the work-sizing and
path-manifest gates.

The change:
- Make work-sizing floor derive PR stats with explicit rename detection.
- Make path-manifest diff gates and staged-index shims use the same
  rename-aware diff shape.
- Add regression coverage for pure relocations, large real changes, and
  rename plus unlisted-path containment failures.

Per-file purpose (the closed path-set - 10 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ce-335-rename-aware-gates.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce-335-rename-aware-gates.md`** *(A)* - this carrier.
- **`validators/creator_engine_validator/carrier_gen.py`** *(M)* - generated carrier path sets use rename-aware name-only diff.
- **`validators/creator_engine_validator/checks/path_manifest_fidelity.py`** *(M)* - path-manifest gates use rename-aware diff consistently.
- **`validators/creator_engine_validator/checks/work_sizing_floor.py`** *(M)* - work-sizing floor uses rename-aware numstat.
- **`validators/creator_engine_validator/cli.py`** *(M)* - CLI help matches the rename-aware gate.
- **`validators/creator_engine_validator/v3_cli.py`** *(M)* - staged/index path-manifest shims mirror the gate command shape.
- **`validators/tests/unit/test_carrier_gen.py`** *(M)* - carrier generator command expectation.
- **`validators/tests/unit/test_path_manifest_fidelity.py`** *(M)* - path-manifest rename containment regressions.
- **`validators/tests/unit/test_work_sizing_floor.py`** *(M)* - work-sizing relocation and large-change regressions.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=1e7ee474e427f1f06b9d81d84a30e86248d4144716650fef745a4224bb19d430

```text
.ce/changelog/ce-335-rename-aware-gates.md
.ce/pr-manifests/ce-335-rename-aware-gates.md
validators/creator_engine_validator/carrier_gen.py
validators/creator_engine_validator/checks/path_manifest_fidelity.py
validators/creator_engine_validator/checks/work_sizing_floor.py
validators/creator_engine_validator/cli.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_carrier_gen.py
validators/tests/unit/test_path_manifest_fidelity.py
validators/tests/unit/test_work_sizing_floor.py
```
