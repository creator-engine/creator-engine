# CE-event Protocol

G2.003.0 defines the substrate for Creator Engine v2 CE-event signed blocks.
It is intentionally write-free: no live event records are emitted by this gate.

## Block shape

A CE-event block contains:

- `block_id`: stable event block identifier.
- `sequence`: monotonic chain index.
- `parent_hash`: null for genesis, otherwise the prior block digest.
- `content_hash`: SHA256 over canonical block material excluding
  `content_hash` and `signature`.
- `emitting_role`: canonical non-ratifying role.
- `operating_mode`: `strict`, `auto`, or `transcendence` context.
- `recorded_at`: UTC timestamp.
- `event`: structured payload with kind, subject, and summary.
- `signature`: shape-only mapping. The value remains reserved-inactive.

## Content addressing

Canonical serialization uses JSON with stable key ordering and compact
separators. `content_hash` is excluded to avoid self-reference. `signature` is
also excluded because G2.003.0 validates signature shape, not cryptographic
binding.

## Hash-chain invariant

A genesis block uses `parent_hash: null`. Every later block references the prior
block digest. Broken, forked, or reordered chains fail validation.

## Signature field

The signature mapping is present so later gates can introduce key custody and
verification without changing the block shape. In this gate, signature semantics
are deferred and the value remains `reserved-inactive`.

## Role and privileged floor

`agent_ratifier` is reserved-inactive. CE-event blocks may be emitted only by
canonical non-ratifying roles such as `operator`, `controller`, `architect`,
`implementer`, `reviewer`, `verification`, or advisory review roles. A CE-event
block cannot ratify privileged authority.

## Operating-mode context

Blocks record the operating-mode context from the merged G2.002.0 substrate.
Recording `auto` or `transcendence` as context does not activate that mode.
Activation remains separately Operator-ratified.

## State boundary

The future v2 event-state home is `.ce/ce-events/`. G2.003.0 does not write live
records there. Active v2 CE-event state must not be written under the legacy
`.hermes/ce-events/` path.

## Deferred surfaces

The following remain out of scope for this gate:

- live event emission;
- signing and key custody;
- distributed PCL;
- Integration Queue runtime;
- connector runtime;
- GitHub, CI, deploy, or provider settings;
- auto/transcendence runtime activation;
- PR review, approval, merge, and cleanup.

## Validation

The `ce_event_block` validator enforces schema shape, content-address
determinism, chain linkage, role floor, operating-mode enum, signature shape,
no-inline metadata, and the `.hermes/ce-events/` write-freeze.
