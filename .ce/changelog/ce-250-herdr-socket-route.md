---
slug: ce-250-herdr-socket-route
date: 2026-07-17
kind: fixed
scope: VPS runsc
issue: ce-ops#250
---

**Canonical Herdr socket route for VPS runsc seats.**

- Make the image own the fixed container-local Herdr client socket default.
- Use plain exact-name `docker exec` for readiness and operator pane commands.
- Preserve the governed pane's scrubbed environment and refuse host or caller
  socket carriers.
