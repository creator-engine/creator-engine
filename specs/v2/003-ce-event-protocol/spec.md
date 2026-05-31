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

## Runtime slice (G2.003.1)

G2.003.1 turns the G2.003.0 block substrate into an executable, local,
daemonless, network-free `ce event {sign,verify,append,replay,index}` surface.
It writes append-only event chains under the **ignored** `.ce/ce-events/spool/`
zone and reuses the unchanged `ce_event_block` validator for every shape
decision. It adds no new validator/check and no schema change.

### FR-011 — Local append surface

`ce event append` appends one block to a named local chain under
`.ce/ce-events/spool/<stream>/`. The genesis block uses `sequence: 0` and
`parent_hash: null`; each later block takes the next monotonic `sequence` and
sets `parent_hash` to the current head `content_hash`. A head manifest records
the head sequence, content hash, and last block reference, and must agree with
the last block.

### FR-012 — Canonical-hash parity

The runtime `content_hash` MUST be byte-identical to the G2.003.0 canonical-hash
rule (SHA256 over canonical block material excluding `content_hash` and
`signature`). A runtime-produced block, dumped to a CE-event YAML, MUST pass the
**unchanged** `ce_event_block` validator (backward-compatibility canary).

### FR-013 — Verify, replay, and index

`ce event verify` validates an on-disk chain — delegating shape to the landed
`ce_event_block` validator and adding head-manifest agreement — and rejects
forged hashes, broken links, unknown modes, and activated signatures.
`ce event replay` and `ce event index` are deterministic, read-only projections
that are byte-identical across runs for a given chain.

### FR-014 — Privileged floor preserved at runtime

`ce event` may emit only canonical non-ratifying roles; `agent_ratifier` and
`source` are refused. The `signature` mapping stays shape-only with value
`reserved-inactive`; a non-reserved value is refused. The runtime performs no
cryptographic signing, key custody, key rotation, distributed identity, or
credential handling. `ce event sign` only refreshes the shape-only signature and
the content hash.

### FR-015 — Operating-mode context only

`ce event` records `operating_mode` as context. An unknown mode is refused; no
mode is activated and no autonomy is granted in any mode.

### FR-016 — State boundary and fail-closed writes

All runtime event state lands only under the ignored `.ce/ce-events/spool/`
zone; the runtime refuses to write when that root is not git-ignored inside a
repository, and refuses any event targeting the frozen `.hermes/ce-events/`
path. Every refusal is raised before any write, so a refused call leaves the
spool byte-identical.

### FR-017 — Transport-adapter baseline and runtime stop line

The append/read path runs through an injectable transport seam whose default is
local filesystem ("git" = synced by ordinary git, not a CE network call).
Network transports, distributed identity, PCL, Integration Queue, connector,
CI/deploy hooks, GitHub settings, and auto/transcendence activation remain out of
scope for this slice.

## Success criteria

- Well-formed CE-event block examples pass.
- Malformed examples fail with targeted validation codes.
- The new sidecar passes v2 terminology, role enum, sidecar schema, and crosswalk
  checks without mutating `specs/v2/_crosswalk.yml`.
- PR review, approval, merge, and cleanup remain separate Operator-ratified gates.

### Runtime slice (G2.003.1)

- `ce event append` → `ce event verify` round-trips a multi-block chain;
  sequences are contiguous from 0 and `content_hash`/`parent_hash` are correct.
- A runtime-produced block passes the **unchanged** `ce_event_block` validator.
- Every refusal path (role floor, unknown mode, write-freeze, un-ignored spool
  root, non-reserved signature, corrupt head) leaves the spool byte-identical.
- All runtime writes land under the ignored `.ce/ce-events/spool/`; `git status`
  shows no tracked runtime state.
- No new check, no schema change, and no cryptography/key custody are introduced.
