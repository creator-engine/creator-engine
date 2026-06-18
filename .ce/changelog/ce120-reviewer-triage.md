---
slug: ce120-reviewer-triage
date: 2026-06-18
kind: added
scope: reviewer triage
issue: ce-ops#120
---

Added Phase 1-2 reviewer triage: governed reviewer registry and decision
schemas, five schema-valid decision examples, and a plan-only
`ce reviewer-triage plan --pr <n> --json` command.

The planner is offline and ownership-only. It emits auditable eligibility,
availability, assignment, escalation, and non-authority facts without sending
review requests, spawning reviewer venues, minting envelopes, approving,
ratifying, merging, or waiving policy.
