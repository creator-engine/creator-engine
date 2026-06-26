---
slug: ce-286-host-uds-persist
date: 2026-06-26
kind: docs
scope: deploy
issue: ce-ops#286
---

**Document host UDS access for the VPS runsc runtime.**

Captured the `/etc/docker/daemon.json` prerequisite for `--host-uds=open` on the
`runsc-gvproxy-ptrace` runtime and the Docker reload step so contained-seat
broker socket access survives host reprovision. (ce-ops#286)
