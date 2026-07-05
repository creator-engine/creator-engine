---
slug: ce-452-canary-qa-worker-role
date: 2026-07-05
kind: added
scope: worker roles
issue: ce-ops#452
---

**Add governed canary/QA worker role definition.**

- Defines `canary_qa` as a disposable-scratch released-artifact validation role
  with live-artifact egress and sandbox-repository short-TTL credentials only.
- Records stop lines for credential-scope surprises, canonical-repository
  mutation needs, signing needs, and invalid signature/gate evidence.
- Updates the worker role roster so controllers can dispatch the new role
  without broadening runtime wiring.
