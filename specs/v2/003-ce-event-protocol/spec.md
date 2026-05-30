# CE-event protocol (signed blocks)

## Goal

G2.003.0 defines the v2 CE-event signed-block substrate: the record shape,
content-addressing rules, hash-chain invariant, validator, examples, and prose
contract needed before any live event emission exists.

## Scope

This gate is substrate-only. It creates the spec, sidecar, ADR, schema,
validator, examples, and tests for CE-event blocks. It does not write live event
records and does not activate a runtime path.

## Functional requirements

### FR-001 — Canonical block record

A CE-event block MUST carry `block_id`, monotonic `sequence`, `parent_hash`,
`content_hash`, `emitting_role`, `operating_mode`, `recorded_at`, `event`, and a
shape-only `signature` mapping.

### FR-002 — Deterministic content addressing

`content_hash` MUST be the SHA256 digest of a canonical JSON serialization of
the block material, with stable key order, excluding `content_hash` and
`signature` so the digest is not self-referential.

### FR-003 — Hash-chain linkage

The genesis block MUST use `parent_hash: null`. Every non-genesis block MUST set
`parent_hash` to the prior block's `content_hash`. Broken, forked, or reordered
chains fail closed.

### FR-004 — Signature shape only

`signature` is schema-present and shape-validated only. Key custody,
cryptographic signing, verification keys, and signer runtime are deferred to
later gates.

### FR-005 — Privileged floor preserved

`emitting_role` MUST be a canonical non-ratifying role. `agent_ratifier` remains
reserved-inactive and MUST NOT emit or ratify CE-event blocks.

### FR-006 — Operating-mode context

Each block records `operating_mode` as `strict`, `auto`, or `transcendence`.
This is context metadata from the merged G2.002.0 substrate; it does not activate
any runtime autonomy mode.

### FR-007 — Sidecar metadata

Governance metadata for this spec lives in adjacent `spec.ce.yml`, not inline in
Markdown.

### FR-008 — v2 event-state home and write-freeze

The canonical future v2 home is `.ce/ce-events/`. G2.003.0 does not write there
or anywhere else. Active v2 CE-event state MUST NOT be written under the legacy
`.hermes/ce-events/` path.

### FR-009 — Validator coverage

The `ce_event_block` validator MUST enforce schema shape, content-address
determinism, chain linkage, role floor, operating-mode enum, signature shape,
no-inline metadata, and the `.hermes/ce-events/` write-freeze.

### FR-010 — Substrate stop line

Live event emission, key custody, distributed PCL, Integration Queue runtime,
connector runtime, CI/deploy hooks, GitHub settings, and auto/transcendence
runtime activation remain out of scope.

## Success criteria

- Well-formed CE-event block examples pass.
- Malformed examples fail with targeted validation codes.
- The new sidecar passes v2 terminology, role enum, sidecar schema, and crosswalk
  checks without mutating `specs/v2/_crosswalk.yml`.
- PR review, approval, merge, and cleanup remain separate Operator-ratified gates.
