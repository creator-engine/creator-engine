---
slug: ce633-daemon-lease-flake-hardening
date: 2026-07-22
kind: fixed
scope: daemon lease test
issue: ce-ops#633
---

**Harden the queue-daemon heartbeat-failure test under validator contention.**

- Bound the test's completion observation beyond the launcher's existing
  child-reap bound, without changing launcher behavior.
- Replace its PID-reuse-prone child-absence probe with a fake-child TERM
  acknowledgement that is observed only after the launcher exits.
