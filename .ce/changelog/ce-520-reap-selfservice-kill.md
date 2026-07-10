---
slug: ce-520-reap-selfservice-kill
date: 2026-07-10
kind: fixed
scope: reap / stale tmux self-service
issue: ce-ops#520
---

**`ce reap once` now teaches the operator how to clear stale live tmux launch surfaces.**

- Adds tmux-specific operator guidance when a launched/no-exit seat is stale but
  its recorded PID is still live.
- The escalation JSON and escalation record now name the exact tmux session and
  the self-service `tmux kill-session -t ...` command, followed by `ce reap once`.
- Pins the behavior with focused `seat_reaper` policy-layer unit coverage.
