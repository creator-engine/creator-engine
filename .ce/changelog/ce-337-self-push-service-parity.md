---
slug: ce-337-self-push-service-parity
date: 2026-07-17
kind: fixed
scope: self-push broker systemd deployment contract
issue: ce-ops#337
---

**Repair the canonical self-push broker service and installer contract.**

- Run the self-push broker from an administrator-provisioned,
  controller-managed stable checkout and require explicit numeric peer UID/GID
  controls before any credential-bearing path.
- Preserve the systemd-owned activated socket across service restarts and
  migrate the recognized stale `ce-egress-broker-dev3.service` pathname binder
  before enabling the canonical socket/service pair.
- Fail closed on missing stable checkout or peer controls, keep the broker env
  file owner-only, preserve idempotent unit rendering, and document exit-code-3
  configuration refusal and OpenBao ordering.

This is a deployable capability correction only. It does not install or restart
services, update a live stable checkout, access OpenBao, mint credentials, or
perform a live deployment.
