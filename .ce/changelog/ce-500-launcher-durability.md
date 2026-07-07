---
slug: ce-500-launcher-durability
date: 2026-07-07
kind: changed
scope: runsc launchers
issue: ce-ops#500
---

**Runsc launcher durable staging and worktree roots.**

- Stage generated contained Codex configs under each seat's durable log root instead of host /tmp.
- Bind durable host-backed worktree roots to the container /var/tmp worktree root for both VPS and DGX runsc launchers.
- Extend launcher smoke coverage for durable default config paths and symmetric /var/tmp mounts.
