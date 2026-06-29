---
slug: ce-supportagent-discord-adapter
date: 2026-06-29
kind: added
scope: validator support agent
issue: ce-ops#354
---

**Support agent Phase C Discord channel adapter.**

- Adds a dependency-free Discord channel adapter seam for support-agent answers.
- Renders validated support answers with citations, clean refusals, safe fallback errors, and Discord length-bound chunks.
- Covers the adapter with offline unit tests using fake clients and stubbed answerers.
