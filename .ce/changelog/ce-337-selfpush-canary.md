---
slug: ce-337-selfpush-canary
date: 2026-07-02
kind: fixed
scope: vps-runsc egress broker
issue: ce-ops#337
---

**Self-push broker stable socket mount and canary.**

- Fixes the VPS launcher to mount broker socket directories instead of restart-sensitive socket inodes.
- Adds a contained self-push canary that fails on stale broker sockets, broker refusal, or non-no-op responses when requested.
- Documents live diagnosis: dev-3 broker services were running, but the container-held push/review socket mounts returned ECONNREFUSED after daemon restarts.
