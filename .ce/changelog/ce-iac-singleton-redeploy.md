---
slug: ce-iac-singleton-redeploy
date: 2026-07-08
kind: story
scope: deploy/singleton-redeploy, docs/operations
issue: Operator decision 1
---

**Add singleton daemon redeploy surface.**

- Adds a bounded singleton redeploy script for queue-daemon with dry-run planning, env-file mode checks, systemd unit update/reload/restart handling, active-state wait, and health probing.
- Adds a dry-run smoke test and operations runbook for the singleton redeploy workflow.
- Leaves option-a-materializer as an explicit future-target stub.
