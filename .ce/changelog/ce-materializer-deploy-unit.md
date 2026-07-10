---
slug: ce-materializer-deploy-unit
date: 2026-07-10
kind: story
scope: materializer deploy pre-arming
---

**Add dry-run materializer deployment support.**

- Adds a supervised dry-run materializer service, environment template, and health-capable launcher with arming disabled by default.
- Extends singleton redeploy support so operators can dry-run or redeploy the materializer service through the same bounded flow used by existing singleton daemons.
- Adds focused deploy tests for the systemd unit shape, dry-run redeploy path, and rendered health-probe environment.
