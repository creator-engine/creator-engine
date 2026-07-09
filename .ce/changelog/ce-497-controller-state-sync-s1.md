---
slug: ce-497-controller-state-sync-s1
date: 2026-07-09
kind: feature
scope: controller-ops
issue: ce-497
---

**Add controller state snapshot tool.**

Adds a governed, dry-run-by-default controller snapshot tool for arc state, dispatch state, and optional controller memory. Snapshots include a structured manifest, hashes, source identity, timestamp, and portable restore instructions. The shared credential-path policy and fail-closed symlink handling exclude credential-bearing paths, while verified atomic publication keeps manifest hashes and payload bytes coherent and refuses stale output reuse. Memory defaults are derived from the selected repo and can be explicitly overridden. Live push wiring remains out of scope for this slice.
