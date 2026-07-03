---
slug: ce-410-integrator-alloc-wire
date: 2026-07-03
kind: fixed
scope: integrator belt live-repair workspace allocation
issue: ce-ops#410
---

**slice 3: integrator workspace allocation via daemon receipts.**

- Replaced predictable --work-root repair paths with daemon allocator-issued randomized workspaces (allocator.allocate_integrator_workspace receipts).
- Added fail-closed --runtime-root queue-poll wiring and explicit --work-root refusal.
- Cleanup now only proceeds by receipt (no rmtree of deterministic paths).
- Added offline coverage for allocator-backed workspaces, receipt cleanup, and unsafe runtime roots.
- Consumes the daemon path allocator module landed in the prior slice (#758) read-only.
