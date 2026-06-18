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

Amended the eligibility model to compose with ce-ops ADR-0003/ADR-0004:
registry and decision records now carry isolation-domain tier attestations and
containment status, ordinary PR review requires a Tier-2 floor, uncontained
reviewer venues fail closed, Tier-4 remains available for release/root-key/
signing classes, and CE58 live-identity handling remains expected-actor-only
with no token fields.
