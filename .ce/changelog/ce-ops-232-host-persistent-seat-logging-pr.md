---
slug: ce-ops-232-host-persistent-seat-logging-pr
date: 2026-06-25
kind: feat
scope: ce-ops
issue: ce-ops#232
---

**host-persistent contained-seat logging.**

Bind-mount herdr server + codex stderr/crash logs to a host path that survives the --rm container so contained-seat failures are diagnosable host-side. Tests included. (ce-ops#232)
