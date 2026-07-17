---
slug: ce-592-af-unix-temp-root
date: 2026-07-17
kind: fixed
scope: pytest AF_UNIX socket endpoints
issue: ce-ops#592
---

**Use short test roots for AF_UNIX sockets.**

Use short, private test-only AF_UNIX endpoint roots so intentionally long pytest base paths do not exceed platform socket pathname limits, while explicit production socket paths continue to fail closed.
