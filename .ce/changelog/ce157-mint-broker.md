---
slug: ce157-mint-broker
date: 2026-06-23
kind: fixed
scope: shared-App mint broker rate guard
issue: ce-ops#157
base: 7e6a0d743947c84601a565a5dc83dc61ade99800
work_class: feature
---

Repairs the shared-App mint broker PR by enforcing the configured per-user
mint rate guard.

- Adds an in-memory sliding-window cap keyed by a digest of the caller user
  token, avoiding retention of the raw `ghu_` value.
- Refuses over-cap mint requests with `429` before binding or minting, and
  records a secret-free audit denial.
- Keeps normal in-ceiling, bound mint requests working, including separate
  buckets per caller token and new allowance after window expiry.
- Preserves the no-committed-first-party-wheel posture from `main`.
