---
slug: ce-445-c2-daemon-container-plumbing
date: 2026-07-04
kind: changed
scope: deploy/daemons
issue: ce-ops#445
---

**Daemon container launcher env-file, CA-cert, and tmpfs secret custody plumbing.**

- Added guarded `CE_DAEMON_ENV_FILE` support, read-only OpenBao CA cert remapping,
  and tmpfs-backed container paths for daemon secret file custody.
- Extended daemon container runner tests for env-file refusal, CA cert mapping,
  tmpfs args, and byte-identical queue-daemon default argv compatibility.
