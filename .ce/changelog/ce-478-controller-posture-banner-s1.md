---
slug: ce-478-controller-posture-banner-s1
date: 2026-07-17
kind: fix
scope: ce-cli
issue: ce-ops#478
---

**Fail-closed controller posture banner.**

- Require the harness-binary preflight gate before confirming Ring-0 in the read-only posture projection.
- Require controller or foreman role plus confirmed Ring-0 and Ring-1 before the informational banner can report gate-capable.
- Keep the banner inert: it does not create state, resolve secrets, or affect launch and takeover behavior.
