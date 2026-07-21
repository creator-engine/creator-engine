---
slug: ce639-reviewer-terminal-v2
date: 2026-07-21
kind: security
scope: reviewer evidence admission
issue: ce-ops#639
---

**Make reviewer evidence a fail-closed, receipt-bound v2 terminal.**

- Adds the closed `REVIEWED` / `CANNOT_REVIEW` / `BLOCKED` terminal union and rejects legacy prose as audit-only.
- Requires non-empty concrete verification evidence and a one-use, exact-payload receipt before any governed review submission.
- Denies raw shell review writes and prevents synthetic prose approval restoration.
