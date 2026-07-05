---
slug: ce-445-daemon-container-test-gaps
date: 2026-07-05
kind: fixed
scope: validators
issue: ce-ops#445
---

**daemon container env-file/cacert refusal tests and conveyor invocation pin.**

- Added daemon container launcher coverage for missing CE_DAEMON_ENV_FILE and CE_DAEMON_CACERT_FILE refusal paths, asserting clean stderr and no container engine invocation.
- Added a byte-identical default conveyor-daemon invocation pin to preserve existing behavior when optional plumbing variables are unset.
