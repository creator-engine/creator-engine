---
# INVALID: privileged mutation_class (security) ratified by one of its own
# decision_makers — no self-ratification (VAL-DR-SELF-RATIFIED).
kind: decision-record
record_type: adr
schema_version: "1"
id: ADR-0103
title: "Rotate the seat credential broker"
status: accepted
date: 2026-06-06
decision_makers: [alice]
consulted: []
informed: [bob]
review_by: 2026-09-06
mutation_class: security
evidence_refs:
  - kind: issue
    ref: "creator-engine/creator-engine#77"
    tag: broker-issue
ratification:
  ratified_by: alice
  ratified_at: 2026-06-06
  ratification_prompt_sha: "cc33dd44ee55ff66aa77bb88cc99dd00ee11ff22aa33bb44cc55dd66ee77ff88"
---

# Rotate the seat credential broker

A privileged (`security`) decision whose ratifier is its own decision maker —
the check must reject this: the ratifier of a privileged-class decision is the
*other* peer, never the owner.
