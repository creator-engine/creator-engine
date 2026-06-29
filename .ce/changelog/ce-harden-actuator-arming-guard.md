---
slug: ce-harden-actuator-arming-guard
date: 2026-06-29
kind: changed
scope: forge automerge
issue: ce-ops#313
---

**Harden automerge actuator arming guard.**

- **Declared work class:** story
- Hardened the automerge actuator arming guard to require exact lowercase `ceo` decision and live policy run modes before mutation.
- Refused actuation when the live policy kill switch is active, before any `gh` calls.
- Added fail-closed tests for stale or missing live policy state.
- Aligned caller-side actuator tests with live policy re-verification.
