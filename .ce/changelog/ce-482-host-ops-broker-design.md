---
slug: ce-482-host-ops-broker-design
date: 2026-07-07
kind: story
scope: host-ops
issue: ce-ops#482
---

**Design host-ops broker v1 as a narrow host-state repair layer.**

Adds a design-only document for a systemd-supervised host-ops broker that
replaces raw container-runtime socket reachability with fixed, convergent,
audited repair and status verbs.

The design defines the v1 verb contracts, kill-switch and rate-limit behavior,
CE-owned namespace boundaries, pinned ephemeral image requirements, OpenBao
snapshot and restore-drill handling, and host UID/ownership repair expectations
from mixed-ownership host state failures.
