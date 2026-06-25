---
slug: ce239-approval-wall-openbao
date: 2026-06-25
kind: changed
scope: integrator approval capability wall
issue: ce-ops#239
---

Wire `ce queue-daemon` approval-wall runtime to prefer a configured
`SecretIdentityBackend`/OpenBao supplier for the controller-only verifier
secret.

- Added daemon SecretRef/SecretRequest flags for the approval-wall secret.
- Registered the production `openbao` secret-identity backend and replaced the
  no-op OpenBao materializer with file-backed 0600 delivery.
- Kept `CE_APPROVAL_CAPABILITY_SECRET` as the documented bootstrap fallback only
  when no backend is configured.
- Refuse partial backend configuration, empty backend materialization, backend
  transport failure, and fork-unsafe `env:` target refs without consulting env.
- Preserved dormant-by-default behavior when no backend or fallback secret is
  configured.
- Added daemon-path unit coverage proving backend materialization wins over the
  env fallback when both are present and uses file delivery.
- Isolated herdr steering lease unit tests from shared tempdir state under
  xdist.
