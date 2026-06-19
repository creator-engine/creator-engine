---
slug: ce113-openbao-design
date: 2026-06-19
kind: added
scope: secret identity
issue: ce-ops#113
---

Added Phase 0-2 OpenBao secret-identity substrate: the Operator-accepted
ADR-0005 decision record, the controller-approved design addenda for
pre-deployment hard gates, value-free SecretIdentityBackend objects and
registry, a fake backend, value-free grant/ref schemas, and a CI-pure OpenBao
adapter with injected I/O only.

No live OpenBao deployment, migration, unseal, backup, or secret material import
is included.
