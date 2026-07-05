---
slug: ce-445-g9-adapter-uid-model
date: 2026-07-05
kind: fixed
scope: deploy/daemons
issue: ce-ops#445
---

**Daemon container adapter uid and state-root ownership model for Docker.**

- Declared the canonical daemon image uid/gid contract as `CE_DAEMON_IMAGE_UID`
  defaulting to `10001`, and run the container as that uid/gid.
- Changed host-side daemon state prep to create missing roots only, verify
  existing roots without chmod, and fail closed on Docker uid mismatches with a
  copy-pasteable `chown -R <uid>:<uid> <state_root>` remediation.
- Pinned queue and conveyor secret tmpfs mounts with `uid=`/`gid=` options and
  updated the byte-identical container argv tests for the deliberate argv change.
