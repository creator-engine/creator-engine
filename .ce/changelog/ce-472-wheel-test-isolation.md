---
slug: ce-472-wheel-test-isolation
date: 2026-07-06
kind: fixed
scope: wheel-bake validator tests
issue: ce-ops#472
---

**wheel determinism test isolation.**

- Scrub gitignored `validators/build/` and `validators/creator_engine_validator.egg-info/` before the wheel surface determinism assertion.
- Add regressions proving stale artifact directories no longer false-RED the test while genuine nondeterministic wheel bytes still fail.
