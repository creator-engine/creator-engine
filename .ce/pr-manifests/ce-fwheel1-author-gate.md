# PR path manifest - ce-fwheel1-author-gate

ADR-0010 Phase-A on-ramp for ce-ops#164 / F-wheel-1. This slice records the
ratified decision, demotes first-party app-wheel parity out of the author-side
pytest lane, and adds the reusable offline wheel-bake helper. It does not add
the push-to-main bake job, remove the committed wheel, or change installer /
trust-root / release coordination paths.

Base:
`16ef3f1150fe130beea4a9ff5e9139f7be219c6f` (`origin/main` at dispatch).

Per-file purpose:

- **`.ce/changelog/ce164-fwheel1-author-gate.md`** *(A)* - CI-only changelog
  fragment; not install-path-affecting.
- **`.ce/pr-manifests/ce-fwheel1-author-gate.md`** *(A)* - this carrier.
- **`.github/workflows/validate.yml`** *(M)* - deselects
  `wheel_bake_gate` from the author-side offline pytest run; F-wheel-2 owns the
  post-merge bake lane.
- **`docs/decisions/ADR-0010-take-app-wheel-out-of-authored-prs.md`** *(A)* -
  accepted decision record for the hybrid bake-now/uncommit-later sequence.
- **`validators/creator_engine_validator/wheel_bake.py`** *(A)* - typed
  `build_app_wheel_from_source` helper and manifest dataclass.
- **`validators/requirements-dev.txt`** *(M)* - adds dev/test-only offline build
  frontend/backend pins; runtime dependency floor unchanged.
- **`validators/tests/conftest.py`** *(M)* - registers the `wheel_bake_gate`
  marker.
- **`validators/tests/unit/test_packaging_contract.py`** *(M)* - marks only
  repo-current first-party app-wheel parity assertions as `wheel_bake_gate`;
  dependency wheelhouse assertions stay required.
- **`validators/tests/unit/test_wheel_bake.py`** *(A)* - red/green coverage for
  helper manifest digest, version/source-commit, console-script surface parity,
  deterministic surface, and typed failure.
- **`validators/tests/unit/test_wheelhouse_built_surface.py`** *(M)* - marks the
  existing first-party app-wheel surface parity file as `wheel_bake_gate`.
- **`validators/wheelhouse-dev/build-1.3.0-py3-none-any.whl`** *(A)* -
  offline dev/test build frontend.
- **`validators/wheelhouse-dev/pyproject_hooks-1.2.0-py3-none-any.whl`** *(A)* -
  build frontend dependency.
- **`validators/wheelhouse-dev/setuptools-82.0.1-py3-none-any.whl`** *(A)* -
  offline build backend for `--no-isolation`.
- **`validators/wheelhouse-dev/wheel-0.47.0-py3-none-any.whl`** *(A)* - wheel
  build backend helper.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - app-wheel digest reproduced
  after rebuilding from this branch's source.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`**
  *(M)* - regenerated first-party app wheel so the explicit bake gate remains
  runnable on this transition branch.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=16

AUTHORIZED_PATHS_SHA256=5e2c7bc535dfef33c4f41bb64e3091c58c3fa1bbe764949b106fd43f79a5b2bf

```text
.ce/changelog/ce164-fwheel1-author-gate.md
.ce/pr-manifests/ce-fwheel1-author-gate.md
.github/workflows/validate.yml
docs/decisions/ADR-0010-take-app-wheel-out-of-authored-prs.md
validators/creator_engine_validator/wheel_bake.py
validators/requirements-dev.txt
validators/tests/conftest.py
validators/tests/unit/test_packaging_contract.py
validators/tests/unit/test_wheel_bake.py
validators/tests/unit/test_wheelhouse_built_surface.py
validators/wheelhouse-dev/build-1.3.0-py3-none-any.whl
validators/wheelhouse-dev/pyproject_hooks-1.2.0-py3-none-any.whl
validators/wheelhouse-dev/setuptools-82.0.1-py3-none-any.whl
validators/wheelhouse-dev/wheel-0.47.0-py3-none-any.whl
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
