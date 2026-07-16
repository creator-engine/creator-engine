---
slug: ce-535-queue-logsdir-regression-guard
date: 2026-07-16
kind: test
scope: validators
issue: ce-ops#535
---

**Add queue-daemon log directory regression guard.**

- Add hermetic systemd-unit coverage requiring the queue daemon to declare `LogsDirectory=ce-queue-daemon` and `LogsDirectoryMode=0700`.
