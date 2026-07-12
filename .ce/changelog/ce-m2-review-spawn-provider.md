---
slug: ce-m2-review-spawn-provider
date: 2026-07-12
kind: added
scope: forge
issue: M2
---

**Governed review-acting spawn provider — core (M2 part 1).**

- Adds a default-OFF, flock-claimed, strict JSON provider primitive without forge, queue, or attestation authority.
- Defaulted pending Operator policy: capacity=0, timeout=180 seconds, retention=86400 seconds, and sandbox attestation is disabled until explicitly configured.
- Production deployment, alert routing, and recovery ownership remain unassigned pending Operator policy.
- Retry budget remains the existing shared acting budget; the provider records per-failure outcome codes without allocating a new retry budget.
