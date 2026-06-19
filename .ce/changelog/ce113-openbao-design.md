---
slug: ce113-openbao-design
date: 2026-06-19
kind: added
scope: secret identity
issue: ce-ops#113
---

Added Phase 3 OpenBao local-only deployment planning and live-adapter bootstrap
helpers on top of the already-merged Phase 0-2 substrate: response-wrapped
AppRole unwrap/login, stdlib HTTPS runner, B.2 topology checks, B.3
operator-side unseal/backup/emergency-revocation runbook records, B.4
co-tenancy refusal for governance roots, and B.5 audit-fail-closed probe
automation. The live integration test stands up OpenBao 2.5.5 only as a
disposable loopback sandbox when `CE_OPENBAO_BIN` is set.

No shared/production OpenBao provisioning, migration, production unseal, backup
custody, or real secret-zero injection is included. B.6 migration remains held.
