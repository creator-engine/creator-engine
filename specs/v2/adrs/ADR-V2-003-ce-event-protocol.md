# ADR-V2-003: CE-event protocol signed-block substrate

## Status

Accepted for G2.003.0 draft substrate.

## Context

Creator Engine v2 needs a deterministic event substrate before runtime systems
can emit, relay, or consume governance events. The event substrate must preserve
the Operator-only privileged floor, support operating-mode context, and avoid
creating premature key custody or distributed runtime obligations.

## Decision

G2.003.0 defines CE-event blocks as content-addressed, hash-chained records with
a shape-only signature field. The gate ships docs, schema, validator, examples,
tests, and sidecar metadata only.

The signature field is present so later gates can bind real signing and key
verification without changing the base record shape. G2.003.0 does not implement
signing, key custody, distributed PCL, queue/connector runtime, live event
emission, GitHub settings, CI hooks, or deploy hooks.

## Consequences

- Draft PR authoring can proceed in parallel with G2.002.1 because this gate is
  a layer-2 substrate with mostly new files.
- The only known shared append surface is the validator check registry import.
  Any landing conflict there is serialized PR fan-in work.
- Merge readiness remains a separate Operator-ratified review/approval/merge
  workflow.
- Future runtime gates can depend on a stable block shape without retrofitting
  CE-event metadata later.

## Non-ratification statement

This ADR records a design decision for the PR candidate. It ratifies no future
runtime authority, no privileged-floor relaxation, and no agent ratification.
