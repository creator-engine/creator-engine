---
kind: decision-record
record_type: adr
schema_version: "1"
id: ADR-0201-n1-solo
title: "N=1 native-mode example — honest solo ratification"
status: accepted
date: "2026-06-10"
decision_makers: [ce-architect-seat]
consulted: []
informed: []
review_by: "2026-12-10"
mutation_class: governance
evidence_refs:
  - kind: doc
    ref: "docs/contracts/peer-authority.md (N=1 native mode)"
    tag: pa-contract
ratification:
  ratified_by: solo-gh
  ratified_at: "2026-06-10"
  ratification_prompt_sha: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  quorum: n1_solo
---

# N=1 native-mode example — honest solo ratification

A privileged (`governance`) accepted Decision Record under a **one-human**
coordination policy. The sole resolved human (`solo-gh` → `solo-operator`)
ratified a decision authored by a distinct seat label (`ce-architect-seat`,
which does not resolve to a human). The record honestly carries
`ratification.quorum: n1_solo`, so both `decision_record` (shape) and
`peer_authority` (the map-sensitive cross-check) pass. It auto-expires the
instant the co-located `identity_map` gains a second human.
