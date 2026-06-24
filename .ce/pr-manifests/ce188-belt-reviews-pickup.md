# PR path manifest - ce188-belt-reviews-pickup

## Summary

Implements ce-ops#188 review-pickup routing for the autonomous belt.

## Paths

- `.ce/changelog/ce188-belt-reviews-pickup.md` *(A)* - changelog fragment.
- `.ce/pr-manifests/ce188-belt-reviews-pickup.md` *(A)* - this manifest.
- `validators/creator_engine_validator/pickup.py` *(M)* - review-pickup planner/apply path and stale-review reconciliation wiring.
- `validators/creator_engine_validator/ce_cli.py` *(M)* - `ce pickup reviews` command.
- `validators/tests/unit/test_pickup.py` *(M)* - offline deterministic review-pickup tests.

## Verification

```text
PYTHONPATH=/home/ce-dev-3/ce188-reviews/validators:/workspace/creator-engine/.venv-test/lib/python3.14/site-packages python3 -m pytest validators/tests/unit/test_pickup.py -k 'review_pickup or pickup_reviews' validators/tests/unit/test_re_review.py
PYTHONPATH=/home/ce-dev-3/ce188-reviews/validators:/workspace/creator-engine/.venv-test/lib/python3.14/site-packages python3 -m pytest validators/tests/unit/test_re_review.py
python3 -m py_compile validators/creator_engine_validator/pickup.py validators/creator_engine_validator/ce_cli.py validators/tests/unit/test_pickup.py
```
