---
slug: ce-l7e-parity
date: 2026-06-30
kind: feature
scope: release automation
issue: L7/day-arc
---

**Add release parity promotion gate.**

- Adds a post-finalize release parity workflow that waits for Pages propagation, verifies the live signed release against checked-out docs and the release tag SHA chain, then promotes the draft GitHub release to latest.
- Closes the matching AWAITING-OPERATOR signing issue only after parity passes.
