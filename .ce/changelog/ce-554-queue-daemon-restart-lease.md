---
slug: ce-554-queue-daemon-restart-lease
date: 2026-07-14
kind: changed
scope: queue daemon singleton lease startup
issue: ce-ops#554
---

**Queue-daemon restart lease recovery.**

- Restrict queue-daemon startup recovery to an audited same-host lease whose positive integer PID is proven absent.
- Preserve fail-closed refusal for malformed, live, permission-limited, and cross-host lease records while retaining SIGTERM lease release.
- Add hermetic launcher-level coverage for malformed and ineligible automatic-recovery records without lease replacement or audit success.
