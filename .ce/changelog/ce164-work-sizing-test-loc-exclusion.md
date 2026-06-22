# ce164 work-sizing test LOC exclusion

- Amend the G5 work-sizing PR-diff floor so class ceilings are applied to
  source/non-test added LOC, excluding added lines in `validators/tests/**`,
  `test_*.py`, and `*_test.py` files.
- Add regression coverage proving a diff with source additions plus larger test
  additions is sized by the source additions only.
