# PR path manifest - ce-334-packaging-test-skip-guard - ce-ops#334 schema packaging test skip guard

- **Declared work class:** story

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-334-packaging-test-skip-guard

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified:
ce-ops#334 closes the schema packaging coverage gap where the integration test
could skip in the offline CI lane when build-backend tooling was unavailable.

The change:
- Build the validator wheel with `python -m build --wheel --no-isolation` so the
  existing offline CI dev install supplies `build` and `setuptools` from
  `validators/wheelhouse-dev/`.
- Add a strict schema-packaging lane switch that turns build, venv, install, and
  console-script setup skips into failures under `CI=true` or local
  `CE_SCHEMA_PACKAGING_STRICT=1`.

Per-file purpose (the closed path-set - 3 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ce-334-packaging-test-skip-guard.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce-334-packaging-test-skip-guard.md`** *(A)* - this carrier.
- **`validators/tests/integration/test_schema_packaging_wheel.py`** *(M)* - use non-isolated offline build tooling and fail strict lanes instead of skipping.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=bd1e86f420b026ec0d2dbbf5318a2dc735186c1e171070d1db35fbb39d7026fd

```text
.ce/changelog/ce-334-packaging-test-skip-guard.md
.ce/pr-manifests/ce-334-packaging-test-skip-guard.md
validators/tests/integration/test_schema_packaging_wheel.py
```
