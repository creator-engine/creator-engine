---
kind: decision-record
record_type: adr
schema_version: "1"
id: ADR-0202-n1-solo-expired
title: "Auto-expiry example — n1_solo under a two-human map"
status: accepted
date: "2026-06-10"
decision_makers: [ce-architect-seat]
consulted: []
informed: []
review_by: "2026-12-10"
mutation_class: governance
evidence_refs:
  - kind: doc
    ref: "docs/contracts/peer-authority.md (N=1 native mode — auto-expiry)"
    tag: pa-contract
ratification:
  ratified_by: op-one-gh
  ratified_at: "2026-06-10"
  ratification_prompt_sha: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
  quorum: n1_solo
---

# Auto-expiry example — n1_solo under a two-human map

The same `quorum: n1_solo` claim as the valid fixture, but the co-located
coordination policy now resolves **two** distinct humans. The solo carve-out is
no longer valid: `peer_authority` fails this record with
`VAL-PA-N1-SOLO-EXPIRED`. From here a privileged decision needs the real
two-human quorum; the marker cannot outlive the one-human condition.
