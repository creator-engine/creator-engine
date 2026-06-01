# PCL Protocol

G2.004.0 defines the substrate for Creator Engine v2 PCL (Project Coordination
Ledger) records. PCL is the per-repo authoritative coordination ledger. This
gate is intentionally write-free: no live ledger records are emitted and no
`ce pcl` runtime exists yet.

## Record shape

A PCL record contains:

- `record_id`: stable coordination record identifier.
- `record_kind`: the coordination kind discriminator.
- `sequence`: monotonic chain index.
- `parent_hash`: null for genesis, otherwise the prior record digest.
- `content_hash`: SHA256 over canonical record material excluding
  `content_hash` and `signature`.
- `emitting_role`: canonical non-ratifying role.
- `operating_mode`: `strict`, `auto`, or `transcendence` context.
- `recorded_at`: UTC timestamp.
- `body`: kind-specific coordination payload.
- `signature`: shape-only mapping. The value remains reserved-inactive.

## Record kinds

A PCL record is discriminated by `record_kind`, one of: `lane_claim`,
`lane_release`, `gate_opened`, `gate_closed`, `completion_report_pointer`,
`event_block_pointer`, `directive_pack_published`, or `identity_assertion`.
Unknown kinds fail validation.

## Content addressing

Canonical serialization uses JSON with stable key ordering and compact
separators. `content_hash` is excluded to avoid self-reference. `signature` is
also excluded because G2.004.0 validates signature shape, not cryptographic
binding.

## Hash-chain invariant

A genesis record uses `parent_hash: null`. Every later record references the
prior record digest. Broken, forked, or reordered chains fail validation.

## CE-event pointer (decoupled)

An `event_block_pointer` record references a CE-event block by an opaque 64-hex
`ce_event_content_hash` value carried in its `body`. The PCL substrate imports no
CE-event code or schema and has no runtime dependency on the CE-event protocol
gate; the two layers are linked only by value.

## Signature field

The signature mapping is present so later gates can introduce key custody and
verification without changing the record shape. In this gate, signature semantics
are deferred and the value remains `reserved-inactive`.

## Role and privileged floor

`agent_ratifier` is reserved-inactive. PCL records may be emitted only by
canonical non-ratifying roles such as `operator`, `controller`, `architect`,
`implementer`, `reviewer`, `verification`, or advisory review roles. PCL
aggregation is read-only coordination state and can never ratify privileged
authority.

## Operating-mode context

Records carry the operating-mode context from the merged G2.002.0 substrate.
Recording `auto` or `transcendence` as context does not activate that mode.
Activation remains separately Operator-ratified.

## State boundary

The future v2 ledger-state home is `.ce/pcl/` (records/ tracked-or-synced;
cache/ gitignored). G2.004.0 does not write live records there. Active v2 PCL
state must not be written under the legacy `.hermes/pcl/` path.

## Deferred surfaces

The following remain out of scope for this gate:

- live ledger emission and the `ce pcl` runtime;
- `.ce/pcl/` live writes;
- signing and key custody;
- federated identity and distributed claim;
- Integration Queue runtime;
- connector runtime;
- GitHub, CI, deploy, or provider settings;
- auto/transcendence runtime activation;
- PR review, approval, merge, and cleanup.

## Validation

The `pcl_record` validator enforces schema shape, content-address determinism,
chain linkage, record-kind enum, role floor, operating-mode enum, event-block
pointer shape, signature shape, no-inline metadata, and the `.hermes/pcl/`
write-freeze.

## Runtime (G2.004.1)

`G2.004.1` adds the local, daemonless, network-free `ce pcl` runtime over the
per-repo authoritative `.ce/pcl/` state. It reuses the `pcl_record` validator for
every shape decision and imports no CE-event or distributed-identity code.

### Commands

- `ce pcl append --ledger <id> --pcl-root .ce/pcl --record-id <id> --record-kind <kind> --emitting-role <role> --operating-mode <mode> --recorded-at <ts> --body-json <json>`
  — validates and content-addresses a record on the chain head, then atomically
  writes it (and the head manifest) under `.ce/pcl/records/<ledger>/`. Every
  refusal raises before any write.
- `ce pcl verify --ledger <id> --pcl-root .ce/pcl` — reconstructs and validates
  the chain fail-closed (shape, content addressing, linkage, floor, head).
- `ce pcl replay --ledger <id> --pcl-root .ce/pcl` — deterministic ordered
  read-only projection.
- `ce pcl index --ledger <id> --pcl-root .ce/pcl` — deterministic content-hashed
  index written to the **git-ignored** `.ce/pcl/cache/<ledger>/`.
- `ce pcl merge --source <a> --source <b> --target <t> --pcl-root .ce/pcl` —
  deterministic conflict-detecting union of ≥2 verified ledgers (fails closed on
  a fork; never mutates authoritative records; writes a projection to the cache).

### State boundary

`.ce/pcl/records/` is the per-repo authoritative, **tracked-or-synced**
coordination ledger (records are committed/synced, not ignored). The rebuildable
`.ce/pcl/cache/` (index/merge projections) is **git-ignored** and never
authoritative. Active writes under legacy `.hermes/` paths are refused.

### Floors

No cryptography or key custody — `signature` stays shape-only `reserved-inactive`.
The canonical non-ratifying `emitting_role` floor is enforced at `append`;
`agent_ratifier`/`source` may not emit; PCL never ratifies; the runtime records
operating-mode context only and activates no autonomy. Real signing, key custody,
the federated-identity / distributed-claim runtime, and connector/queue runtime
remain deferred to later, separately ratified gates.
