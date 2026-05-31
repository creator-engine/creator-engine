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

## CE-event runtime (G2.003.1)

G2.003.1 turns the substrate into a local, daemonless, network-free `ce event`
surface. It adds no new validator and no schema change, introduces no
cryptography or key custody, and activates no autonomy. It writes append-only
event chains under the **ignored** instance-local zone
`.ce/ce-events/spool/<stream>/`.

### Commands

```text
ce event append   # append one shape-only-signed block to a local chain
ce event verify   # validate an on-disk chain + head manifest (read-only)
ce event sign     # refresh a draft block's shape-only signature + content hash
ce event replay   # deterministic ordered read-only projection of a chain
ce event index    # deterministic content-hashed read-only index of a chain
```

A minimal append/verify round-trip:

```text
ce event append --stream demo --event-root .ce/ce-events \
  --block-id ceevt-demo-0000 --emitting-role controller \
  --operating-mode strict --recorded-at 2026-05-30T16:00:00Z \
  --event-json '{"kind":"gate_progress","subject":"G2.003.1","summary":"first block"}'
ce event verify --stream demo --event-root .ce/ce-events
```

### Chain construction

The genesis block uses `sequence: 0` and `parent_hash: null`. Each later block
takes the next monotonic `sequence` and sets `parent_hash` to the current head
`content_hash`. A head manifest records the head sequence, content hash, block
count, and last block reference, and must agree with the last block. The runtime
`content_hash` is byte-identical to the substrate canonical-hash rule, so a
runtime-produced block passes the unchanged `ce_event_block` validator.

### Refusals (fail-closed before any write)

- emitting `agent_ratifier` or `source`, or any non-canonical role
  (`G2-EVENT-ROLE-FLOOR`);
- an unknown `operating_mode` (`G2-EVENT-MODE-INVALID`);
- a non-reserved signature value (`G2-EVENT-SIGNATURE-RESERVED`);
- an event targeting the frozen `.hermes/ce-events/` path
  (`G2-EVENT-WRITE-FREEZE`);
- a spool root that is not git-ignored inside a repository
  (`G2-EVENT-ROOT-NOT-IGNORED`);
- a corrupt head manifest that cannot be safely linked
  (`G2-EVENT-CHAIN-LINK`).

Every refusal is raised before any write, so a refused call leaves the spool
byte-identical.

### State boundary and transport

All runtime event state lands only under the ignored `.ce/ce-events/spool/`
zone — never under the frozen `.hermes/ce-events/` path. The append/read path
runs through an injectable transport seam whose default is the local filesystem
(synced by ordinary git, not a CE network call). Network transports, distributed
identity, PCL, the Integration Queue, connectors, and CI/deploy hooks remain
deferred. The runtime performs no cryptographic signing or key custody; the
signature value stays `reserved-inactive`.
