---
slug: ce263-seat-restart-reliability
date: 2026-06-26
kind: changed
scope: systemd seat supervision
issue: ce-ops#263
---

Changed contained Codex seats to use systemd-supervised restart. The unit now
pre-cleans stale named containers with `ExecStartPre`, runs as `Type=simple`,
keeps `exec docker wait` in the foreground so systemd owns the lifecycle, and
uses `Restart=always`.
