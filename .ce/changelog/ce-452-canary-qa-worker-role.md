---
slug: ce-452-canary-qa-worker-role
date: 2026-07-05
kind: tiny
scope: .claude/agents/canary_qa.md (new worker role) + .claude/agents/README.md roster update + brain-ledger evidence re-pin/broadening (d1b-20-v3) + active-count ratchet + changelog
issue: creator-engine/ce-ops#452
---

**Canary QA worker role.**

- Defines `canary_qa` as a disposable-scratch released-artifact validation role
  with live-artifact egress and sandbox-repository short-TTL credentials only.
- Records stop lines for credential-scope surprises, canonical-repository
  mutation needs, signing needs, and invalid signature/gate evidence.
- Updates the worker role roster so controllers can dispatch the new role
  without broadening runtime wiring.
- Supersedes `brain-assertion-d1b-20-canonical-worker-role-files-v2` -> `-v3`
  to name `canary_qa` as the fifth canonical role and re-pin `evidence_sha256`
  to this branch's own `.claude/agents/README.md`, preserving the ad-hoc-role
  invention guard clause.
