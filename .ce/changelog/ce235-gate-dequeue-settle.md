---
slug: ce235-gate-dequeue-settle
date: 2026-06-25
kind: added
scope: gate-hardening — merge-queue dequeue primitive + integrator settle window
issue: ce-ops#235
---

**gate dequeue + settle.**

- Dequeue primitive (`gh pr merge --disable-auto`) so an already-enqueued PR can be stopped.
- Integrator settle window: re-verify the approval (present, not dismissed, authorized identity) immediately before `--auto`.
- Fail-closed: if re-verification can't confirm a valid approval, do not enqueue.
