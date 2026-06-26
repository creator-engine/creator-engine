---
slug: ce252-validate-pr-ci-parity
date: 2026-06-26
kind: fixed
scope: validator tooling
issue: ce-ops#252
---

**`ce validate-pr` now mirrors the CI offline gate (full tree, not unit-only).**

- **Declared work class:** tiny

- The preflight's default baseline-diff test command (`DEFAULT_TEST_COMMAND`)
  ran `validators/tests/unit` only, which is narrower than CI's offline pytest
  step and produced false-greens (it let integration-test failure #507 through).
- Aligned the default to CI's offline invocation exactly:
  `python -m pytest -p no:cacheprovider validators/tests/ -m "not wheel_bake_gate" -q -n auto --dist loadgroup`,
  restoring true CI parity. The preflight is now slower (~1-4 min) by design.
