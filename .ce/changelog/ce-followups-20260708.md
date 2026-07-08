---
slug: ce-followups-20260708
date: 2026-07-08
kind: fix
scope: validators, host-ops-broker
issue: ce-ops#504
---

**Review follow-up batch for merged PR minors.**

- Tighten host-ops broker fail-closed kill-switch and schema minor findings from merged PR #898.
- Scope seat-ready autogen commits to the regenerated artifact and pin the missing PR #896 test coverage.
- Isolate the stale checkout artifact determinism test in a temporary repo copy; partially addresses #504 minors only, with MAJOR broker arming findings remaining out of scope.
