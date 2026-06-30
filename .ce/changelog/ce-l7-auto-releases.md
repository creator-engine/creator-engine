---
slug: ce-l7-auto-releases
date: 2026-06-30
kind: feature
scope: release automation
issue: L7/day-arc
---

**Automate release staging and post-sign finalization seam.**

- Adds release-tag-safe staging preflight so tag checkouts no longer depend on PR branch discovery.
- Adds a fail-closed `release-finalize` seam that verifies an Operator-provided SSHSIG against ce-root-v1 before preparing publishable artifacts.
- Keeps signing manual and does not publish Pages, mutate releases, approve, merge, or enqueue.
