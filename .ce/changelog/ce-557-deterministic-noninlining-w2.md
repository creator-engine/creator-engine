---
slug: ce-557-deterministic-noninlining-w2
date: 2026-07-13
kind: fixed
scope: validator tooling
issue: ce-ops#557
---

**Deterministic controller no-inlining enforcement.**

- Adds the required path-manifest and changelog carriers for this governed
  feature on branch `ce-557-deterministic-noninlining-w2`.
- Hardens the review-blocked enforcement seams: execution-plane primitives
  fail closed without complete launch-pinned worker identity, inherited
  `CE_WORKER_*` values are scrubbed at the Ring-1 boundary, worker records are
  bound to launcher-controlled worker/record/role/lane/scope/worktree/seat/actor
  and process pins, Ring-1 defaults cover the concrete guarded preflight,
  carrier, extraction, worktree, and harvest-push entry points, shell composition
  fails closed for capability-shaped opaque forms, archive list/test modes remain
  read-only, and spawn identifiers normalize to a closed capability class.
- Records focused rework evidence: `test_hook_check.py` plus
  `test_runner_ring1_tool_guard.py` reported `264 passed` before the full
  governed validator run.
- Corrects the stale full-validator integration expectation so partial
  `CE_WORKER_ID` plus event-selected worker identity remains denied while the
  complete launcher-owned worker environment path stays allowed.
- Corrects the PR #1014 blocking gate findings by resolving deterministic
  first-token env/alias indirection, failing closed on unresolved
  execution-shaped clean parses, and allowing only archive list/test output
  captures while command-substituted extraction and governed execution remain
  opaque-denied.
