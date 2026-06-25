---
slug: ce230-verify-by-reaction
date: 2026-06-25
kind: story
scope: runner / herdr session brief-dispatch confirmation
issue: ce-ops#230
---

**verify brief dispatch by agent reaction.**

Implements verify-by-agent-reaction dispatch confirmation in the herdr session
runner, replacing fragile buffer-echo checks. After a brief is dispatched, the
runner confirms delivery by observing the agent's reaction rather than echoing
the input buffer, closing the ce-ops#230 crit-6 confirmation gap.

Refs ce-ops#230.
