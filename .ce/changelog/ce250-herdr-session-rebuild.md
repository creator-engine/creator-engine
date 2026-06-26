---
slug: ce250-herdr-session-rebuild
date: 2026-06-26
kind: changed
scope: contained seat relaunch
issue: ce-ops#250
---

**Harden relaunch session coverage for contained runsc seats.**

- Confirms DGX/VPS relaunch backs up stale herdr session.json before live Docker launch while preserving CODEX_HOME/sessions.
- Confirms fake herdr readiness exposes only the canonical w1:p1 pane and no stale w2/w3 panes.
