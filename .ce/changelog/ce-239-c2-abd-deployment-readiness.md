---
slug: ce-239-c2-abd-deployment-readiness
date: 2026-07-13
kind: changed
scope: approval-wall deployment readiness
issue: ce-ops#239
---

Add dormant, environment-driven approval-wall deployment coordinates to the
integrator unit, plus OpenBao and bootstrap-fallback operator documentation.
No secret or policy value, live environment action, service action, wall-state
change, or arming act is included. The separate lease-restart change remains
serialized from this carrier because both touch the integrator unit, and they
must never be combined.
