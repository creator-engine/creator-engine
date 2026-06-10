---
kind: decision-record
record_type: adr
schema_version: "1"
id: ADR-0101
title: "Use a single shared backlog on the forge"
status: accepted
date: 2026-06-01
decision_makers: [alice]
consulted: [bob]
informed: []
review_by: 2026-12-01
mutation_class: governance
evidence_refs:
  - kind: doc
    ref: "docs/architecture/coordination.md"
    tag: one-backlog
  - kind: pr
    ref: "creator-engine/creator-engine#42"
    tag: backlog-pr
policy_sha: "1f2e3d4c5b6a79880099aabbccddeeff00112233445566778899aabbccddeeff"
ratification:
  ratified_by: bob
  ratified_at: 2026-06-02
  ratification_prompt_sha: "aa11bb22cc33dd44ee55ff66aa77bb88cc99dd00ee11ff22aa33bb44cc55dd66"
crosswalk:
  informs: [RFC-0102]
---

# Use a single shared backlog on the forge

## Context and Problem Statement

Two peer instances each kept an instance-local idea ledger; actionable items
diverged. We need one shared queue (the A.0 invariant: the forge is the only
shared state).

## Decision Drivers

- One source of truth for "what is next" ([one-backlog]).
- No second backlog in a private ops repo.

## Considered Options

1. One forge backlog, private repos promote into it.
2. Per-instance backlogs with periodic sync.

## Decision Outcome

Chosen option: **1**, because promotion-into-one-queue keeps a single ranked
truth and was already exercised on the forge ([backlog-pr]).

## Consequences

- Good: claims and priorities are team-visible.
- Bad: genuinely-sensitive intel needs a separate authoring tier (see the
  storage-tier policy).
