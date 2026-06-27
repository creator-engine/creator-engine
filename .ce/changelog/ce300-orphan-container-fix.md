---
slug: ce300-orphan-container-fix
date: 2026-06-27
kind: story
scope: deploy/vps-runsc
issue: ce-ops#300
---

**Prevent orphaned VPS runsc probe containers.**

- Add an explicit exact-name pre-launch removal guard before the canonical detached VPS seat launch.
- Ship a conservative host cron artifact that prunes only stopped containers older than 24 hours.
- Document live-container probing via `docker exec` in the internal controller playbook.
