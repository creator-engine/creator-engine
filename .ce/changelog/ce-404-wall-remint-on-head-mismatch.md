---
slug: ce-404-wall-remint-on-head-mismatch
date: 2026-07-02
kind: fixed
scope: integrator belt
issue: ce-404
---

**Wall remint on head mismatch.**

- Treat stale approval-capability markers with `head_mismatch` as remintable only when a trusted authorized current-head approval exists.
- Emit `head_mismatch_no_current_approval` when a stale marker cannot be reminted because no trusted current-head approval is present.
