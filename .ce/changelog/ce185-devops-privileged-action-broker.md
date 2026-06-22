---
slug: ce185-devops-privileged-action-broker
date: 2026-06-22
kind: added
scope: devops privileged-action broker design and envelope schema
issue: ce-ops#185
---

Added design artifacts for the ce-ops#185 DevOps privileged-action broker:
a proposed ADR, a prose contract covering the broker architecture, threat model,
OpenBao capability basis, ce-ops#184 VPS pilot sequence, and a JSON Schema
envelope for ratified privileged-action grants.

This is docs/schema only. It does not implement a runtime broker, deploy OpenBao
mounts, mint live capabilities, perform root actions, merge, or change forge
permissions.
