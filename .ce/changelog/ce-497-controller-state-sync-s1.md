---
slug: ce-497-controller-state-sync-s1
date: 2026-07-09
kind: feature
scope: controller-ops
issue: ce-497
---

**Add controller state snapshot tool.**

Adds a governed, dry-run-by-default controller snapshot tool for arc state, dispatch state, and optional controller memory. Snapshots include a structured manifest, hashes, source identity, timestamp, and restore instructions. A hard denylist excludes credential-bearing paths and records denied paths for audit. Live push wiring remains out of scope for this slice.
