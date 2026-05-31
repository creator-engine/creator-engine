# Distributed Identity Protocol (G2.004.2 substrate)

**Status**: Substrate only. Authored under gate `G2.004.2`. Records and validates
shape only; activates no runtime.

**Source-of-truth**: `specs/v2/004-pcl-substrate/spec.md` (G2.004.2 section) and
`specs/v2/004-pcl-substrate/spec.ce.yml`. Schemas:
`schemas/federated-identity-binding.schema.yaml`,
`schemas/distributed-claim.schema.yaml`. Validator: the
`federated_identity_binding` and `distributed_claim` checks. Examples:
`validators/examples/federated-identity-binding/`,
`validators/examples/distributed-claim/`.

## 1. Purpose

`G2.004.2` adds the two coordination-record families that the team-mode /
multi-repo control plane needs *before* any distributed runtime exists:

- **Federated identity binding** — asserts, as coordination/attestation state
  only, that a named principal in one repository is the same principal as named
  identities in one or more other repositories.
- **Distributed claim** — the cross-repo / team-mode coordination claim
  primitive: the distributed analogue of a single-repo PCL `lane_claim`.

Both families extend feature 004 (PCL) without coupling to PCL or CE-event
runtime code, so this gate is authored in parallel with the CE-event runtime
gate `G2.003.1` and depends only on the merged `G2.004.0` PCL substrate.

## 2. What this gate is NOT

This gate ships docs, schema, validator, examples, tests, spec, sidecar, and ADR
only. It does **not** implement a runtime, write live `.ce/` state, perform
signing or key custody, bind active authority, or activate any operating mode.
The federated-identity / distributed-claim **runtime** is a later, separately
ratified gate. The `deploy`, `governance`, `identity`, and `security` privileged
floors remain Operator-only.

## 3. Federated identity binding record

A federated identity binding is a content-addressed, hash-chained record. The
canonical fields mirror the PCL record shape (see `PCL_PROTOCOL.md`):
`record_id` (prefix `fib-`), `record_kind`, `sequence`, `parent_hash`,
`content_hash`, `emitting_role`, `operating_mode`, `recorded_at`, `body`, and a
shape-only `signature`.

| `record_kind` | meaning |
|---|---|
| `federated_identity_binding` | binds one principal across ≥2 repositories |
| `binding_revocation` | revokes a prior binding, referenced by opaque hash |

Body rules (enforced by `VAL-FIB-BINDING-SHAPE`):

- a `federated_identity_binding` body carries an opaque non-empty `principal_id`
  and a `repo_bindings` list of **at least two** entries, each with opaque
  non-empty `repo_id` and `identity_ref` values;
- a `binding_revocation` body references the revoked binding by an opaque 64-hex
  `revokes_binding` content hash.

Identities and repositories are referenced by **opaque, stable identifiers
only** — never secret material, key bytes, tokens, or credentials.

## 4. Distributed claim record

A distributed claim is a content-addressed, hash-chained record with `record_id`
prefix `dc-`. Its `record_kind` is one of `claim_open`, `claim_renew`, or
`claim_release`.

Body rules (enforced by `VAL-DC-POINTER-SHAPE`):

- every claim body carries an opaque non-empty `claim_subject`;
- every claim body binds to a federated identity binding by an opaque 64-hex
  `binding_ref`;
- optional `ce_event_content_hash` and `pcl_content_hash` pointers, when present,
  MUST be opaque 64-hex content hashes.

By referencing CE-event blocks and PCL records **only** by opaque content hash,
a distributed claim records its coordination context without importing
CE-event or PCL code or schema. This decoupling is the same discipline the PCL
substrate uses for its `event_block_pointer` (G2.004.0 FR-007).

## 5. Invariants (fail-closed)

Both families fail closed on:

- **content addressing** — `content_hash` MUST equal the SHA256 of the canonical
  JSON serialization of the record material (stable key order, excluding
  `content_hash` and `signature`);
- **hash-chain linkage** — genesis `parent_hash` is `null`; every non-genesis
  `parent_hash` equals the prior record's `content_hash`; broken, forked, or
  reordered chains fail closed;
- **record-kind discrimination** — unknown kinds fail closed;
- **role floor** — `emitting_role` is a canonical non-ratifying role;
  `agent_ratifier` (and the legacy `source`) are reserved-inactive and MUST NOT
  emit; these records never ratify;
- **operating-mode context** — `operating_mode` is `strict`, `auto`, or
  `transcendence`, recorded as context only with no runtime activation;
- **signature shape** — `signature` is schema-present and shape-validated only,
  with `value` pinned to `reserved-inactive`;
- **no inline metadata** — record metadata lives in sidecars/examples, never
  inline in Spec Kit Markdown;
- **legacy write-freeze** — records MUST NOT target legacy `.hermes/` paths as
  active v2 coordination/identity state. The canonical future home is under
  `.ce/`.

## 6. State boundary

The canonical future home for these records is under `.ce/` (per the `G2.001.0`
state boundary: `records/` tracked-or-synced, `cache/` git-ignored). `G2.004.2`
writes no active `.ce/` state and freezes active writes under `.hermes/`.

## 7. Verification

- `validators/tests/unit/test_distributed_identity.py` exercises well-formed and
  malformed fixtures for both families and the CE-event/PCL decoupling invariant.
- The `federated_identity_binding` and `distributed_claim` checks reject each
  malformed example with its targeted `VAL-FIB-*` / `VAL-DC-*` code and accept
  the well-formed examples.
