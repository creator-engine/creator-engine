---
slug: ce-599-canonical-runtime-policy
date: 2026-07-18
kind: security
scope: canonical runtime-policy artifact and launch binding
issue: ce-ops#599
work_class: epic
---

**security(runtime): byte-pin the canonical controller-seat policy**

Adds the canonical controller runtime-policy source with independent semantic
and exact-byte digests, deterministic onboarding render and provenance receipt,
and fail-closed one-shot launch enforcement before runner side effects. Live
launches bind an immutable per-dispatch policy copy and recheck source, render,
receipt, registry, ownership, mode, and descriptor identity at the final
boundary. The slice does not provision seats, handle subscription credentials,
enable the deferred DGX venue, or perform any provider login or deployment act.
