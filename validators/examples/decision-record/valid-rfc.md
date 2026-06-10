---
kind: decision-record
record_type: rfc
schema_version: "1"
id: RFC-0102
title: "Converge the two competing claim-record drafts"
status: accepted
date: 2026-06-03
decision_makers: [bob]
consulted: [alice]
informed: []
review_by: 2026-12-03
mutation_class: schema
evidence_refs:
  - kind: doc
    ref: "schemas/forge-claim.schema.yaml"
    tag: claim-schema
disposition: merge
fcp:
  opened_at: 2026-06-04
  concerns:
    - name: lease-window-shape
      status: resolved
    - name: idempotency-key-derivation
      status: resolved
ratification:
  ratified_by: alice
  ratified_at: 2026-06-05
  ratification_prompt_sha: "bb22cc33dd44ee55ff66aa77bb88cc99dd00ee11ff22aa33bb44cc55dd66ee77"
crosswalk:
  supersedes: [ADR-0099]
  informs: []
---

# Converge the two competing claim-record drafts

## Summary

Adopt the lease-window claim-record draft; deterministically close the
TTL-field draft (superseded with link).

## Motivation

Two peers proposed incompatible claim shapes; an ADR cannot converge a
disagreement — the FCP instrument tracks and resolves the blocking concerns.

## Guide-level explanation

A claim carries `(repo, item_id, claimant_instance, lease_window)` and an
idempotency key derived from exactly that tuple ([claim-schema]).

## Drawbacks and alternatives

The TTL-field draft was simpler but could not express randomized back-off
windows; closed via `crosswalk.supersedes`.

## Final Comment Period log

- `lease-window-shape` — raised by alice, resolved by pinning the window to an
  ISO-8601 interval.
- `idempotency-key-derivation` — raised by bob, resolved by deriving the key
  deterministically from the claim tuple.
