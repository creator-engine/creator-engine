---
slug: ce-484-ephemeral-controller-seam-design
date: 2026-07-07
kind: story
scope: controller providers
issue: ce-ops#484
---

**Ephemeral controller provider seam design.**

Adds a design-only provider seam for event-spawned, self-retiring ephemeral controllers. The design defines mandate-pointer-in and forge-results-out provider contracts, provider-specific postures for self-hosted webhook receivers, GitHub Actions jobs, and managed agent clouds, and fail-closed rules keeping singleton gate custody, approval-wall authority, and SSHSIG signing custody outside ephemeral contexts. It also specifies takeover-compatible evidence packets, lifecycle flow, and validation gates before any non-read-only promotion.
