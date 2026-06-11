---
kind: decision-record
record_type: adr
schema_version: "1"
id: ADR-0203-laundered-quorum
title: "Laundered-quorum example — two accounts of one human, no honest marker"
status: accepted
date: "2026-06-10"
decision_makers: [account-a]
consulted: []
informed: []
review_by: "2026-12-10"
mutation_class: governance
evidence_refs:
  - kind: doc
    ref: "docs/contracts/peer-authority.md (N=1 native mode — laundered quorum)"
    tag: pa-contract
ratification:
  ratified_by: account-b
  ratified_at: "2026-06-10"
  ratification_prompt_sha: "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
---

# Laundered-quorum example — two accounts of one human, no honest marker

A privileged (`governance`) accepted Decision Record under a **one-human** map.
The author stamp (`account-a`) and the ratifier (`account-b`) are two GitHub
accounts of the **same** human (`solo-human`), arranged to *look* like an
independent maker/ratifier pair — and the record omits `quorum: n1_solo`. The
labels are string-distinct, so the `decision_record` self-ratification check
(which compares labels) does not fire; but `peer_authority` resolves both to ONE
human and fails the record with `VAL-PA-N1-SOLO-REQUIRED`: accounts do not sum
to humans, so the privileged floor of 2 is unreachable and the honest solo mode
must be recorded.
