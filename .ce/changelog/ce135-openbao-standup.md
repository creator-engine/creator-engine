---
slug: ce135-openbao-standup
date: 2026-06-22
kind: added
scope: secret identity
issue: ce-ops#135
---

Added proposed ADR-0012 for the OpenBao dedicated secret-store micro-unit
stand-up design: single-node dev profile, HA production path, AppRole machine
auth, KV v2 identity storage, SSH certificate signing preference, Transit
guardrails, seal/unseal and audit posture, and explicit dev/test/prod
separation.

Added a small `LocalSecretIdentityBackend` compatibility implementation behind
the existing `SecretIdentityBackend` protocol so current host-local secret refs
can be modeled value-free while future callers remain backend-agnostic.

No live OpenBao server, deployment, secret migration, runtime caller wiring,
schema change, or wheel rebuild is included.
