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
