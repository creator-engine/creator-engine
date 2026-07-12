---
slug: ce-m2-review-spawn-provider-design
date: 2026-07-11
kind: design
scope: M2 governed review-acting spawn provider
work_class: story
---

Adds the ratification-ready, default-OFF contract for a provider which obtains
an immutable PR-head reviewer worktree, collects a bounded reviewer finding,
and hands caller-owned evidence to the pure M4 ratifier queue. This carrier is
design only: it makes no provider, deployment, or ratifier-state change.
