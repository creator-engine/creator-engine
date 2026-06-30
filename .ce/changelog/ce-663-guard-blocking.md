---
slug: ce-663-guard-blocking
date: 2026-06-30
kind: fixed
scope: validator CI gates
issue: ce-ops#364
---

**Make install-spec signature guard blocking.**

- Flipped the install-spec signature guard from advisory to blocking in CI and local preflight.
- Added focused regression coverage for blocking failures and passing signed specs.
