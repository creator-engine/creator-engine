---
slug: ce-405-mediated-brain-append-adr
date: 2026-07-05
kind: added
scope: governance / brain ledger append ADR
issue: ce-ops#405
---

**Propose a mediated append design for the hash-chained brain assertion ledger.**

Adds ADR-0005 for `.ce/brain/assertions.yaml` append serialization. The ADR
evaluates queue-daemon mediation, merge-queue-native chain recomputation, and a
ledger-file lock primitive; recommends a separate brain-append daemon for the
minimal Phase-1 slice; and records fail-closed, containment, gate-singleton, and
ce-411 duplicate-ID/tombstone invariant requirements.

Design only: no implementation, no ledger schema change, and no `.ce/brain/**`
mutation.
