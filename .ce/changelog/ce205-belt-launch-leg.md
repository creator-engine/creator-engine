---
slug: ce205-belt-launch-leg
date: 2026-06-26
kind: feat
scope: ce-ops
issue: ce-ops#205
---

Teach the pickup belt launch leg to satisfy the governed lane-launch contract
offline: bootstrap the lane brain ledger, bind the worktree path explicitly,
fail closed before materializing invalid repo roots, and cover poll-to-launch
with deterministic unit and offline e2e harnesses.
