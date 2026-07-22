---
slug: ce610-workflow-registry-staleness
date: 2026-07-22
kind: changed
scope: validator workflow-permission audit
issue: ce-ops#610
---

**Fail closed on stale workflow permission profiles.**

- Refuse governed permission profiles whose workflow files are absent, and cover the permissionless unregistered-workflow advisory branch.
