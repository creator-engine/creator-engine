---
kind: decision-record
record_type: adr
schema_version: "1"
id: ADR-0001
title: "Public/private storage policy — the written tier-choice rule"
status: accepted
date: "2026-06-10"
decision_makers: [ce-gate-architect]
consulted: [chmod735]
informed: []
review_by: "2026-12-10"
mutation_class: governance
evidence_refs:
  - kind: doc
    ref: "ce-v35c-strangeloop-coordination-design-20260609.md (Operator-ratified design, §A.3/§A.2)"
    tag: design-a3
  - kind: doc
    ref: "ce-ops ADR-0001 public/private ops architecture (private ops repo)"
    tag: ops-adr
  - kind: doc
    ref: "docs/contracts/storage-tier-finding.md"
    tag: finding-contract
policy_sha: "c16f1749fe8c29d658cef6ad60c94339b5f3cbf3afa578c25e5d799772cb85ea"
ratification:
  ratified_by: chmod735
  ratified_at: "2026-06-10"
  ratification_prompt_sha: "c16f1749fe8c29d658cef6ad60c94339b5f3cbf3afa578c25e5d799772cb85ea"
crosswalk:
  informs: []
---

# Public/private storage policy — the written tier-choice rule

## Context and Problem Statement

A CE instance continuously produces knowledge artifacts (designs, findings,
retrospectives, competitive notes). CE operates two shared surfaces — the
**public OSS code repo** and a **single private ops repo** — plus each
instance's private local state. Which artifact belongs where must be a
**written, ratified rule**, not a per-artifact judgment call: the
public/private boundary cannot be unilaterally rewritten or silently drifted
([design-a3], [ops-adr]).

This ADR is that rule. It is itself a `governance`-class Decision Record —
the rule for classification is the same kind of object as the things it
classifies, with the same governance: **changing it requires the full
privileged ratification bar** (for two peers: both; today: the Operator).

## Decision Drivers

- Confidential material must never reach the public surface by default.
- Project knowledge must travel with the repo (onboarding, audit).
- One backlog: a private surface never becomes a second queue.

## Considered Options

1. A written three-tier policy, ratified as a Decision Record.
2. Per-artifact ad-hoc judgment by whoever authored it.

## Decision Outcome

Chosen option: **1**. The tiers and their rule ([design-a3]):

| Tier | What lands there | Default for |
| --- | --- | --- |
| `instance-local` | working state, transient notes, instance-local noise | anything not affirmatively classified shareable |
| `repo-docs` | project-relevant, **public-safe** knowledge: architecture, contracts, conventions, accepted Decision Records | docs that must travel with the code |
| `ops-private` | project-relevant but **genuinely sensitive**: strategy, competitive intel mid-version-dev, security findings, unredacted post-mortems | confidential project knowledge |

Rules:

1. **Default = private.** When in doubt, an artifact stays `instance-local`
   (or `ops-private` if it must be shared with the team); promotion toward a
   more public tier is the deliberate, human-ratified move — never the
   default ([ops-adr]).
2. **Classification is advisory; placement is ratified.** The classifier
   emits an advisory `storage-tier-finding` ([finding-contract]); a human
   ratifies the tier and any promotion (spine-recorded). No finding
   self-promotes.
3. **Splits are normal.** One artifact may split across tiers (architecture
   half public, strategy half private).
4. **One backlog.** `ops-private` may *author* items privately, but every
   actionable conclusion is promoted (human-ratified) into the single
   code-repo backlog — the private surface never becomes a second queue.
5. **Noise stays local.** A part classified instance-local noise is never
   proposed into a shared tier.

## Consequences

- Good: the boundary is machine-checkable (`storage_tier_finding` +
  `decision_record` checks) and cannot drift silently.
- Good: confidential-never-public becomes policy, not habit.
- Bad: promotion friction is deliberate — sharing requires a ratification
  step. Accepted: that friction *is* the control.
