---
kind: decision-record
record_type: adr
schema_version: "1"
id: ADR-0605
title: "Standing rider cadence and no-change evidence"
status: proposed
date: "2026-07-18"
decision_makers: [ce-dev-3]
consulted: []
informed: []
review_by: "2026-10-18"
mutation_class: governance
evidence_refs:
  - kind: doc
    ref: "docs/decisions/ce605-standing-rider-notes.ndjson"
    tag: rider-notes
  - kind: doc
    ref: "validators/creator_engine_validator/schemas/standing-rider-note.schema.yaml"
    tag: note-schema
---

# Standing rider cadence and no-change evidence

## Status

Proposed. This record does not activate the rider. An accepted status requires
the existing human-ratification evidence defined by the Decision Record
contract.

## Decision

CE605 has one canonical evidence stream at
`docs/decisions/ce605-standing-rider-notes.ndjson`. Notes are sorted-key UTF-8
JSON with one trailing newline, carry an SHA-256 predecessor chain, and are
validated without network access or mutation.

The cadence is seven days. Each accepted note carries the next due boundary.
When a boundary is reached, exactly one note is due; a later boundary is
derived from the prior accepted due boundary, not from a wall-clock poll.
Missing intervals require a deferred assessment or immediate review.

`no_change` is evidence only when authenticated source references and a clear
tripwire are present. Unavailable sources require `source_unavailable`; stale,
contradictory, changed, or deferred inputs require immediate review. Advisory
research may be cited only as a class, public-safe path or opaque digest, and
SHA-256 digest. The validator does not fetch, promote, research, write this
stream, or record a side-effect ledger entry.

## Authenticated checkpoint

- CE605 stream head: `sha256:e51f68ab613a0a0273da8ee7746ab88b89f82322dbc8a8a8f875a62b98142527`

## Authenticated source bindings

- `finding:ce605-initial`: `sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`
