---
slug: ce-482-broker-v1-slice1
date: 2026-07-08
kind: added
scope: host-ops broker v1 slice 1
issue: host-ops-broker-v1
---

**Add Slice 1 of the host-ops broker v1 library.**

Implements the pure-stdlib host-side broker package skeleton with strict request
and verb schemas, secret-free append-only audit, fail-closed config and kill
switch handling, per-caller/per-target rate limits, dict-in/dict-out dispatch,
and injectable adapters for the `status` and `restart-daemon` verbs. Deferred
v1 verbs ship schema validation only in this slice.

Adds focused unit coverage for envelope validation, all nine verb schemas, audit
secret refusal, kill-switch ordering, rate limits, status behavior, and
restart-daemon convergence/audit boundaries.
