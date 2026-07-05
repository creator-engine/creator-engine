---
slug: ce-444-queue-daemon-startup-lease
date: 2026-07-04
kind: changed
scope: validators/creator_engine_validator/v3_cli.py
issue: ce-ops#444
---

**Fail-closed queue daemon startup lease.**

- Added a default-on singleton lease to the Python `ce queue-daemon` entrypoint
  before the first daemon pass, including clean held/stale refusal output.
- Added queue-daemon lease heartbeat and release coverage, plus operator
  recovery notes for stale lease cleanup.
- The daemon now recognizes when its own singleton lease is already held by a
  live, verified ancestor process (its own launcher supervisor) and proceeds
  straight into normal startup instead of refusing — fixing a startup
  deadlock under the canonical launcher while keeping every other refusal
  path (unrelated live holder, stale lease) unchanged and fail-closed.
