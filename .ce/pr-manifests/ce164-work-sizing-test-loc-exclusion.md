# PR path manifest - ce164-work-sizing-test-loc-exclusion

## Intent

Operator-ratified amendment to ce-ops#164 / G5: the work-sizing floor should
size PRs on source/non-test added LOC rather than penalizing safety-test
coverage. Test additions are excluded from the PR-diff class ceiling.

## Verification

Run:

```bash
PYTHONPATH=validators python3 -m creator_engine_validator verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce164-work-sizing-test-loc-exclusion .
PYTHONPATH=validators python3 -m creator_engine_validator verify-work-sizing-floor --base <PR base sha> --declared-work-class story .
PYTHONPATH=validators .venv-test/bin/python -m pytest validators/tests/unit/test_work_sizing_floor.py validators/tests/unit/test_work_sizing_floor_ci_wiring.py -q
```

## Path Set

- **`.ce/changelog/ce164-work-sizing-test-loc-exclusion.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce164-work-sizing-test-loc-exclusion.md`** *(A)* - this closed path-set carrier.
- **`validators/creator_engine_validator/checks/work_sizing_floor.py`** *(M)* - excludes test added LOC from the PR-diff class ceiling path.
- **`validators/tests/unit/test_work_sizing_floor.py`** *(M)* - regression for source-plus-test added LOC classification.

## Paths

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=a5853daca66bf3f5c9377888568ace2ff1e17f4feb937dce656f077f20cabdf0

```text
.ce/changelog/ce164-work-sizing-test-loc-exclusion.md
.ce/pr-manifests/ce164-work-sizing-test-loc-exclusion.md
validators/creator_engine_validator/checks/work_sizing_floor.py
validators/tests/unit/test_work_sizing_floor.py
```
