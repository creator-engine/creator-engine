---
slug: ce127-forge-identity-bind
date: 2026-06-18
kind: fixed
scope: installer forge identity binding
base: 4b62822
---

Bind install-time local forge commits to the per-dev onboard GitHub identity
instead of ambient host `git config`.

The adoption scaffold path now refuses unresolved forge identity, writes
local-only `user.name` / `user.email` plus `user.useConfigOnly=true`, verifies
the committed author, and surfaces the resolved identity in scaffold evidence.
