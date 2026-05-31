# ADR-V2-004: PCL (Project Coordination Ledger) record substrate

## Status

Accepted for G2.004.0 draft substrate.

## Context

Creator Engine v2 needs a deterministic per-repo coordination ledger substrate
before runtime systems can append, verify, replay, or merge coordination state.
PCL (Project Coordination Ledger) is the per-repo authoritative coordination
record. The substrate must preserve the Operator-only privileged floor, support
operating-mode context, reference CE-event blocks without coupling to them, and
avoid creating premature key custody or distributed runtime obligations.

## Decision

G2.004.0 defines PCL records as content-addressed, hash-chained records
discriminated by `record_kind`, with a shape-only signature field. The gate ships
docs, schema, validator, examples, tests, and sidecar metadata only.

PCL aggregation is read-only coordination state and never ratifies anything;
`agent_ratifier` stays reserved-inactive and cannot emit. An `event_block_pointer`
record references a CE-event block only by an opaque 64-hex `ce_event_content_hash`
value, so the PCL substrate imports no CE-event code/schema and carries no runtime
dependency on G2.003.1 — this decoupling is what lets G2.004.0 and G2.003.1 be
authored in parallel. The signature field is present so later gates can bind real
signing and key verification without changing the base record shape.

G2.004.0 does not implement the `ce pcl` runtime, `.ce/pcl/` live writes,
signing, key custody, federated identity, distributed claim, queue/connector
runtime, live ledger emission, GitHub settings, CI hooks, or deploy hooks. The
runtime gate G2.004.1 depends on both G2.004.0 and G2.003.1.

## Consequences

- Draft PR authoring can proceed in parallel with G2.003.1 because this gate is
  a layer-2 substrate with mostly new files.
- The only known shared append surface is the validator check registry import.
  G2.003.1 does not edit that registry; any landing conflict there is serialized
  PR fan-in work.
- Merge readiness remains a separate Operator-ratified review/approval/merge
  workflow; canonical-branch integration is serialized with G2.003.1.
- Future runtime gates can depend on a stable PCL record shape without
  retrofitting coordination metadata later.

## Non-ratification statement

This ADR records a design decision for the PR candidate. It ratifies no future
runtime authority, no privileged-floor relaxation, and no agent ratification.
