---
# INVALID: status superseded with no crosswalk.superseded_by link —
# supersede-don't-delete requires a resolvable successor
# (VAL-DR-SUPERSEDED-UNRESOLVED).
kind: decision-record
record_type: adr
schema_version: "1"
id: ADR-0104
title: "Per-instance backlogs with periodic sync"
status: superseded
date: 2026-05-20
decision_makers: [bob]
consulted: [alice]
informed: []
review_by: 2026-11-20
mutation_class: docs
evidence_refs:
  - kind: doc
    ref: "docs/architecture/coordination.md"
    tag: sync-design
crosswalk:
  informs: []
---

# Per-instance backlogs with periodic sync

A superseded record that names no successor — the supersession link is the
deletion-substitute and must resolve.
