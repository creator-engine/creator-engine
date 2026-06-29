---
slug: ce-armb-broker-runmode
date: 2026-06-29
kind: added
scope: egress self-review broker systemd deployment
issue: ce-ops#356
---

**Surface-B broker run-mode deployment wiring.**

- **Declared work class:** story
- Wires deployed self-review systemd units to their dedicated run-mode env file while preserving the inert dev default.
- Documents Operator arming/rollback as a later env flip plus restart; this change performs no live restart or arming.
