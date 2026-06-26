---
slug: ce11-test-tier-split
date: 2026-06-26
kind: changed
scope: validator test suite — fast/slow tier split
issue: ce-ops#11
---

Implements step-4 of the ce-ops#11 test tier-split plan: tags the full
integration test suite with `@pytest.mark.slow` and all unit tests with
`@pytest.mark.fast`, adds the corresponding markers to `pyproject.toml`, and
introduces a new `validators/tests/unit/test_tier_split.py` guard that asserts
every test file is tagged with exactly one tier marker.

This makes `pytest -m fast` a sub-10-second feedback loop (unit-only) and
`pytest -m slow` the full integration suite, with no uncategorized tests
permitted. The `validators/README.md` is updated with the new invocation
patterns.
