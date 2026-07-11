---
slug: ce-f2-logsdirectory-bind
date: 2026-07-11
kind: fix
scope: deploy
---

**F-2.1b repair: restore `LogsDirectory=`/`LogsDirectoryMode=` binding in `ce-queue-daemon.service`.**

The `ce-f2-gate-hardening` PR (#969's successor) merged F-2.1 (homeless-log
fallback chain), F-2.2 (disk-headroom pre-lease refusal), and F-2.3 (atomic
liveness-state export) into main. The `LogsDirectory=ce-queue-daemon` /
`LogsDirectoryMode=0700` binding that lets systemd provision the log directory
and inject it as `LOGS_DIRECTORY` was omitted from the merged service file.

This patch restores the two missing lines so the F-2.1 `LOGS_DIRECTORY`
environment fallback is provisioned automatically on service start rather than
depending on `CE_DAEMON_LOG_DIR` being set externally.
