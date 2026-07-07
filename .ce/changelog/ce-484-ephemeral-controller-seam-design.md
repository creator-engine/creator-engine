---
slug: ce-484-ephemeral-controller-seam-design
date: 2026-07-07
kind: story
scope: controller providers
issue: ce-ops#484
---

**Ephemeral controller provider seam design.**

Adds a design-only provider seam for event-spawned, self-retiring ephemeral controllers. The design defines mandate-pointer-in and forge-results-out provider contracts, provider-specific postures for self-hosted webhook receivers, GitHub Actions jobs, and managed agent clouds, and fail-closed rules keeping singleton gate custody, approval-wall authority, and SSHSIG signing custody outside ephemeral contexts. It also specifies takeover-compatible evidence packets, lifecycle flow, and validation gates before any non-read-only promotion.

Review remediation on 2026-07-07:

- Names NanoClaw as the T0 reference implementation for the event-spawn -> mandate -> post -> self-retire loop, due 2026-07-21, bound to `self_hosted_webhook_v1`.
- Adds orphan detection, timeout/heartbeat, reap, and partial forge-output cleanup policy per provider, including the lifecycle failure edge.
- Explicitly refuses ephemeral seat-relaunch and `ce launch` authority.
- Names follow-up schema and registry artifacts for `ephemeral_controller.run_v1` and `ce.ephemeral_controller.evidence.v1`.
- Requires the always-on webhook listener to be IaC-deployed and SSOT-fed.
- Marks the `ce-mandate://sha256/` resolver owner/storage decision as blocking for mandate-resolving implementation slices.
