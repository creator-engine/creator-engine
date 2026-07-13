---
slug: ce-557-deterministic-noninlining-w2
date: 2026-07-13
kind: fixed
scope: validator tooling
issue: ce-ops#557
---

**Deterministic controller no-inlining enforcement.**

- Adds the required path-manifest and changelog carriers for this governed
  story on branch `ce-557-deterministic-noninlining-w2`.
- Hardens the review-blocked enforcement seams: execution-plane primitives
  fail closed without launch-pinned worker identity, worker records are bound
  to launcher-controlled `CE_WORKER_*` pins, Ring-1 defaults cover the concrete
  guarded entry points, and primitive classification uses parsed command
  entry points instead of substring regexes.
- Records focused rework evidence: `test_hook_check.py` reported 200 passed
  and `test_runner_ring1_tool_guard.py` reported 22 passed before the full
  governed validator run.
