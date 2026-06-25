---
slug: ce234-credential-wall-approval
date: 2026-06-25
kind: added
scope: integrator approval capability wall
issue: ce-ops#234
---

Require a controller-minted approval capability before the integrator daemon can
enqueue an approved PR for auto-merge.

- Added a pure forge approval-capability signer/verifier with HMAC-SHA256,
  injected secret supplier, deterministic payloads, expiry, policy binding, and
  secret-free audit records.
- Extended daemon candidate parsing to read PR body markers and reviewer logins.
- Made raw GitHub approval necessary but insufficient: approved/current-head PRs
  now fail closed with `approval_capability_missing` or
  `approval_capability_invalid` unless a valid wall marker is present.
- Documented the controller-only approval-wall model and updated focused daemon
  and version-boundary tests.
