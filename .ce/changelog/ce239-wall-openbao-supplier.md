---
slug: ce239-wall-openbao-supplier
date: 2026-06-26
kind: changed
scope: integrator approval capability wall
issue: ce-ops#239
---

Record the residual ce-ops#239 supplier gate on top of the already-merged
approval-wall OpenBao wiring.

credential-wall MUST NOT be armed in production until this lands AND the daemon
sources its secret from OpenBao; this PR is the wiring, not the arming.

- Verified the daemon path already imports `secret_identity` and prefers the
  `SecretIdentityBackend`/OpenBao supplier when backend configuration is
  provided.
- Verified the env supplier remains a bootstrap fallback only when no backend is
  configured.
- Left production wall state, credential custody, signing root, workflows,
  rulesets, CODEOWNERS, and launcher runtime untouched.
