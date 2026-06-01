# ADR-V2-004-1: PCL runtime (`ce pcl`)

## Status

Accepted for G2.004.1 draft runtime.

## Context

The merged G2.004.0 PCL record substrate (`checks/pcl_record.py` +
`schemas/pcl-record.schema.yaml`) defined the shape-only, content-addressed,
hash-chained PCL record. With G2.003.1 (CE-event runtime) merged, the PCL
runtime's dependency floor (G2.004.0 + G2.003.1) is satisfied, so the per-repo
authoritative coordination ledger can gain an executable, local, daemonless,
network-free surface. This slice lands after the G2.004.2 substrate slice because
G2.004.1 was dependency-gated on G2.003.1.

## Decision

G2.004.1 adds `validators/creator_engine_validator/pcl_runtime.py` and a `pcl`
subcommand group on the `ce` CLI: `append`, `verify`, `replay`, `index`, `merge`.
It mirrors the landed `ce_event_runtime` (append-only hash chain + head manifest,
injectable transport, read-only `git check-ignore` guard) and **reuses the
G2.004.0 validator for every shape decision**, so a runtime-produced record is
byte-for-byte the artifact `pcl_record` already accepts.

Key boundary decisions:

- **State boundary differs from CE-events.** Per the G2.001.0 state boundary and
  the v1→v2 crosswalk, `.ce/pcl/records/` is the per-repo authoritative
  **tracked-or-synced** ledger (NOT git-ignored, unlike the CE-event spool); only
  the rebuildable `.ce/pcl/cache/` (index/merge projections) is git-ignored. The
  runtime refuses writing records under a legacy `.hermes/` path.
- **No cryptography / no key custody.** `signature` stays shape-only
  `reserved-inactive`; the runtime introduces no signing or verification keys.
- **Operator-only privileged floor.** `agent_ratifier`/`source` may not emit; the
  runtime records operating-mode context only and activates no autonomy; PCL
  never ratifies.
- **Decoupling preserved.** `pcl_runtime` imports no CE-event or
  distributed-identity code; CE-event references stay opaque 64-hex pointers
  validated by the landed `pcl_record` check (AST-asserted in tests).
- **`merge` is read-only and conflict-detecting.** It unions verified ledgers,
  fails closed on any fork, never mutates authoritative records, and writes only
  a projection to the ignored cache.

Every refusal raises before any write, so a refused call leaves the records dir
byte-identical.

## Consequences

- The PCL coordination ledger is now appendable/verifiable/replayable/indexable/
  mergeable locally and offline, with records committed/synced as authoritative
  state and rebuildable projections kept out of the tree.
- Self-validation against the landed schema means the record shape stays
  authoritative in one place (G2.004.0); the runtime cannot drift from it.
- Later gates can bind real signing, federated-identity/distributed-claim
  runtime, and connector/queue runtime on a stable PCL runtime without
  retrofitting.

## Non-ratification statement

This ADR records a design decision for the PR candidate. It ratifies no future
runtime authority, no privileged-floor relaxation, no signing/key custody, and no
agent ratification.
