---
slug: ce-388-fastfollow-lease-ux
date: 2026-07-04
kind: fixed
scope: conveyor daemon
issue: ce-ops#388
---

**Fast-follow conveyor daemon lease UX and one-shot launcher flag.**

- Added clean direct-entrypoint lease refusal handling with exit 73.
- Renamed the launcher finite-pass flag to `--one-shot` and made `--dry-run` fail closed.
- Documented stuck lease verification and recovery.
