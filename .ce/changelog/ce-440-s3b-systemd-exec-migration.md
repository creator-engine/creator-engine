---
slug: ce-440-s3b-systemd-exec-migration
date: 2026-07-04
kind: changed
scope: systemd gate daemons
issue: ce-ops#440
---

**Migrate repo systemd units from cev3 to ce.**

- Migrated the integrator and review pickup systemd units to invoke the unified `ce` CLI surface while preserving daemon arguments.
- Updated the gate daemon systemd test prefix assertion to allow `ce` and bash launchers only.
