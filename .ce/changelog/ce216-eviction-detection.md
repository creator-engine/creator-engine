---
slug: ce216-eviction-detection
date: 2026-06-23
kind: added
scope: integrator eviction detection
issue: ce-ops#216
---

Adds the Unit 1 read-only integrator detector for approved, green PRs that need
repair before integration.

- Adds a v3 forge `eviction_detection` module that polls bounded Search API PR
  candidates and re-reads GitHub's computed PR state through the existing
  `pr_state` GraphQL helper.
- Emits deterministic structured `repair-needed` events for explicitly
  recognized dirty, behind, or conflicting states, preserving GitHub's exact
  `mergeStateStatus` and `mergeable` values.
- Keeps executor behavior out of scope; this slice only observes and emits
  events for later repair execution.
