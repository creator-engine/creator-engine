---
slug: ce234-credential-wall-approval
date: 2026-06-25
kind: added
scope: integrator approval capability wall
issue: ce-ops#234
---

Add an enforce-when-armed controller approval capability wall for the integrator
daemon.

- Added a pure forge approval-capability signer/verifier with HMAC-SHA256,
  injected secret supplier, deterministic payloads, expiry, policy binding, and
  secret-free audit records.
- Extended daemon candidate parsing to read PR body markers and reviewer logins.
- Made raw GitHub approval a dormant fallback until a wall secret is configured;
  once armed, approved/current-head PRs fail closed with capability or wall
  misconfiguration refusals unless a valid wall marker is present.
- Added an explicit `SecretIdentityBackend`/OpenBao supplier adapter with
  injected materialized-value reading and value-free audit/state handling.
- Wired `ce queue-daemon` to resolve and persist wall armed state, and added
  `ce approval-capability mint` for controller marker issuance.
- Documented the controller-only approval-wall model and updated focused daemon
  and CLI tests.
