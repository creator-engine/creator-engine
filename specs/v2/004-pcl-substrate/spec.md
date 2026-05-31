# PCL substrate (Project Coordination Ledger records)

## Goal

G2.004.0 defines the v2 PCL (Project Coordination Ledger) record substrate: the
content-addressed record shape, the hash-chain invariant, the record-kind
discriminator, the validator, examples, and prose contract needed before any
live coordination-ledger runtime exists. PCL is the per-repo authoritative
coordination ledger; this gate ships substrate only.

## Scope

This gate is substrate-only. It creates the spec, sidecar, ADR, schema,
validator, examples, and tests for PCL records. It does not write live ledger
records, does not provide a `ce pcl` runtime, and does not activate a `.ce/pcl/`
write path. The runtime (`ce pcl` append/verify/replay/index/merge and any
`.ce/pcl/` live write) is G2.004.1 and depends on both G2.004.0 and G2.003.1.

## Functional requirements

### FR-001 — Canonical PCL record

A PCL record MUST carry `record_id`, a `record_kind` discriminator, monotonic
`sequence`, `parent_hash`, `content_hash`, `emitting_role`, `operating_mode`,
`recorded_at`, a kind-specific `body`, and a shape-only `signature` mapping.

### FR-002 — Deterministic content addressing

`content_hash` MUST be the SHA256 digest of a canonical JSON serialization of
the record material, with stable key order, excluding `content_hash` and
`signature` so the digest is not self-referential.

### FR-003 — Hash-chain linkage

The genesis record MUST use `parent_hash: null`. Every non-genesis record MUST
set `parent_hash` to the prior record's `content_hash`. Broken, forked, or
reordered chains fail closed.

### FR-004 — Record-kind discrimination

`record_kind` MUST be one of the canonical PCL kinds: `lane_claim`,
`lane_release`, `gate_opened`, `gate_closed`, `completion_report_pointer`,
`event_block_pointer`, `directive_pack_published`, or `identity_assertion`.
Unknown kinds fail closed.

### FR-005 — Privileged floor preserved; PCL never ratifies

`emitting_role` MUST be a canonical non-ratifying role. PCL aggregation is
read-only coordination state and never ratifies anything. `agent_ratifier`
remains reserved-inactive and MUST NOT emit or ratify PCL records.

### FR-006 — Operating-mode context

Each record records `operating_mode` as `strict`, `auto`, or `transcendence`.
This is context metadata from the merged G2.002.0 substrate; it does not activate
any runtime autonomy mode.

### FR-007 — CE-event pointer by opaque hash

An `event_block_pointer` record MUST reference a CE-event block only by an
opaque 64-hex `ce_event_content_hash` value carried in its `body`. The substrate
MUST NOT import or depend on CE-event code/schema, keeping PCL and the CE-event
protocol decoupled.

### FR-008 — Signature shape only

`signature` is schema-present and shape-validated only. Key custody,
cryptographic signing, verification keys, and signer runtime are deferred to
later gates.

### FR-009 — Sidecar metadata

Governance metadata for this spec lives in adjacent `spec.ce.yml`, not inline in
Markdown.

### FR-010 — v2 ledger-state home and write-freeze

The canonical future v2 home is `.ce/pcl/`. G2.004.0 does not write there or
anywhere else. Active v2 PCL state MUST NOT be written under the legacy
`.hermes/pcl/` path.

### FR-011 — Validator coverage

The `pcl_record` validator MUST enforce schema shape, content-address
determinism, chain linkage, record-kind enum, role floor, operating-mode enum,
event-block pointer shape, signature shape, no-inline metadata, and the
`.hermes/pcl/` write-freeze.

### FR-012 — Substrate stop line

Live ledger emission, `ce pcl` runtime, `.ce/pcl/` live writes, federated
identity runtime, distributed claim runtime, connector runtime, key custody,
CI/deploy hooks, GitHub settings, and auto/transcendence runtime activation
remain out of scope.

## Success criteria

- Well-formed PCL record/chain examples pass.
- Malformed examples fail with targeted validation codes.
- The new sidecar passes v2 terminology, role enum, sidecar schema, and crosswalk
  checks without mutating `specs/v2/_crosswalk.yml`.
- The CE-event block substrate and all prior checks/examples remain unchanged.
- PR review, approval, merge, and cleanup remain separate Operator-ratified gates.

# G2.004.2 — Federated identity binding + distributed claim substrate

## Goal

G2.004.2 defines two additional shape-only feature-004 record families: the
**federated identity binding** (cross-repo identity binding) and the
**distributed claim** (cross-repo / team-mode coordination claim primitive). It
is substrate only and depends only on the merged G2.004.0 PCL substrate; it is
authored in parallel with the CE-event runtime gate G2.003.1.

## Scope

This gate creates the protocol doc, two schemas, validator checks
(`federated_identity_binding`, `distributed_claim`), examples, tests, and this
spec/sidecar/ADR extension. It does not implement a runtime, write live `.ce/`
state, sign records, custody keys, bind active authority, or activate any
operating mode. The federated-identity / distributed-claim runtime is a later,
separately ratified gate. It imports no federated-identity, CE-event, or PCL
runtime code.

## Functional requirements

### FR-013 — Canonical federated identity binding record

A federated identity binding record MUST carry `record_id` (prefix `fib-`), a
`record_kind` discriminator (`federated_identity_binding` or
`binding_revocation`), monotonic `sequence`, `parent_hash`, `content_hash`,
`emitting_role`, `operating_mode`, `recorded_at`, a kind-specific `body`, and a
shape-only `signature` mapping.

### FR-014 — Cross-repo binding shape

A `federated_identity_binding` body MUST carry an opaque non-empty `principal_id`
and a `repo_bindings` list of at least two entries, each with opaque non-empty
`repo_id` and `identity_ref`. A `binding_revocation` body MUST reference the
revoked binding by an opaque 64-hex `revokes_binding` hash. Identities and repos
are referenced by opaque, stable identifiers only — never secret material.

### FR-015 — Canonical distributed claim record

A distributed claim record MUST carry `record_id` (prefix `dc-`), a `record_kind`
discriminator (`claim_open`, `claim_renew`, `claim_release`), `sequence`,
`parent_hash`, `content_hash`, `emitting_role`, `operating_mode`, `recorded_at`,
a `body`, and a shape-only `signature`.

### FR-016 — Claim binding and opaque pointers

A distributed claim body MUST carry an opaque non-empty `claim_subject` and bind
to a federated identity binding by an opaque 64-hex `binding_ref`. Optional
`ce_event_content_hash` and `pcl_content_hash` pointers, when present, MUST be
opaque 64-hex content hashes. The substrate MUST NOT import federated-identity,
CE-event, or PCL code/schema, keeping these families decoupled.

### FR-017 — Deterministic content addressing and chain linkage

For both families, `content_hash` MUST be the SHA256 digest of a canonical JSON
serialization of the record material (stable key order, excluding `content_hash`
and `signature`). The genesis record MUST use `parent_hash: null`; every
non-genesis record MUST set `parent_hash` to the prior record's `content_hash`.
Broken, forked, or reordered chains fail closed.

### FR-018 — Privileged floor preserved; records never ratify

`emitting_role` MUST be a canonical non-ratifying role. Federated identity
bindings and distributed claims are read-only coordination state and never
ratify anything. `agent_ratifier` remains reserved-inactive and MUST NOT emit.

### FR-019 — Operating-mode context, signature shape, no inline metadata

Each record records `operating_mode` as `strict`, `auto`, or `transcendence`
(context only). `signature` is schema-present and shape-validated only with
`value` pinned to `reserved-inactive`. Record metadata MUST live in sidecars and
examples, never inline in Spec Kit Markdown.

### FR-020 — State home and write-freeze

The canonical future home is under `.ce/`. G2.004.2 does not write there or
anywhere else. Records MUST NOT target legacy `.hermes/` paths as active v2
coordination/identity state.

### FR-021 — Validator coverage

The `federated_identity_binding` and `distributed_claim` checks MUST enforce
schema shape, content-address determinism, chain linkage, record-kind enum, role
floor, operating-mode enum, body/pointer shape, signature shape, no-inline
metadata, and the `.hermes/` write-freeze, each with a targeted `VAL-FIB-*` /
`VAL-DC-*` code.

### FR-022 — Substrate stop line

Live record emission, distributed-identity/claim runtime, `.ce/` live writes,
signing, key custody, federated identity runtime, connector, queue, CI/deploy
hooks, GitHub settings, and auto/transcendence runtime activation remain out of
scope.

## Success criteria (G2.004.2)

- Well-formed federated-identity-binding and distributed-claim examples pass.
- Malformed examples fail with targeted `VAL-FIB-*` / `VAL-DC-*` codes.
- The extended sidecar passes v2 terminology, role enum, sidecar schema, and
  crosswalk checks without mutating `specs/v2/_crosswalk.yml`.
- The CE-event block substrate, the G2.004.0 PCL substrate, and all prior
  checks/examples remain unchanged; the new validator imports no CE-event or PCL
  code.
- PR review, approval, merge, and cleanup remain separate Operator-ratified
  gates; canonical-branch integration is serialized with G2.003.1.
