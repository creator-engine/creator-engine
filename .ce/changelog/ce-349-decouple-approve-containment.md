---
slug: ce-349-decouple-approve-containment
date: 2026-06-28
kind: changed
scope: forge review broker
issue: ce-ops#349
---

**Decouple APPROVE authority from containment.**

- Gates APPROVE on author separation, reviewer-authority envelope, and run-mode policy instead of containment substrate.
- Keeps current solo/team run-modes default-deny for autonomous APPROVE; only future strangeLoop can pass with a valid reviewer envelope.
- Carries a token-free checked-authority fact into the transport deputy so raw APPROVE remains fail-closed while gate-valid proxy dispatch can pass.
- Adds broker/proxy/policy regression coverage for self-author refusal, envelope denial, the allowed future path, raw transport denial, and substrate parity.
