---
slug: ce250-herdr-session-json-relaunch
date: 2026-06-25
kind: changed
scope: contained seat relaunch
issue: ce-ops#250
---

**Clear stale herdr session on contained relaunch.**

- Backs up stale herdr session.json before live DGX/VPS contained-seat Docker launch so Codex relaunches on w1:p1.
- Adds regression coverage for prelaunch backup and dry-run no-mutation behavior.
