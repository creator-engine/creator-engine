# Worktree Lease Protocol

**Status**: Parallel Controller Orchestration (PCO) Slice 2A normative
protocol. Substrate-only. Layered onto, and subordinate to, the
Feature 001 governance substrate, the Feature 002 operating model,
and the Slice 0 / Slice 1/2 Active-Work Ledger primitives. A fresh
clone is sufficient to apply this protocol; no external tracker
credential or network state is required.

## a. Purpose

Slice 1/2's [`./ACTIVE_WORK_LEDGER_PROTOCOL.md`](./ACTIVE_WORK_LEDGER_PROTOCOL.md)
detects a worktree-path collision *only after* both colliding ledger
claims exist on disk. Until a Controller can register an
**intent-to-write** before the claim is written, two Source-ratified
Controllers cannot rehearse multi-lane authoring safely; they can
only race and then read the loss.

This protocol defines that intent-to-write primitive: the **Worktree
Lease**. Slice 2A introduces the tracked lease record schema, the
prose contract here, and additive predicates in the existing
`active_work_ledger_conflicts` validator that refuse pre-launch state
when (a) a live claim's worktree is not covered by a live lease under
the same controller, or (b) two controllers hold live leases on the
same worktree. Slice 2A is substrate-only: it does **not** allocate
worktrees, does **not** mutate `git worktree` state, and does **not**
ship a `pco-allocate` / `pco-release` CLI. Those mechanics are
reserved for a separately ratified Slice 2R follow-on.

## b. Source-of-truth relationship

| Upstream source of truth | Role |
|---|---|
| Feature 001 governance substrate | Author/approver separation; privileged-class enumeration; ratification flow. |
| Feature 002 operating model | Assignment-Envelope contract; verifies-not-ratifies; authority-conflict halt path. |
| [`../architecture/parallel-agent-development-model.md`](../architecture/parallel-agent-development-model.md) | One-driver-per-worktree rule; the parallel-pair shape. |
| [`../architecture/parallel-controller-orchestration.md`](../architecture/parallel-controller-orchestration.md) | Architectural companion to this protocol. |
| [`./ACTIVE_WORK_LEDGER_PROTOCOL.md`](./ACTIVE_WORK_LEDGER_PROTOCOL.md) | Companion prose contract for the Active-Work Ledger; the lease layer sits beside, not above, the ledger. |
| [`./CONTROLLER_BOUNDARY_POLICY.md`](./CONTROLLER_BOUNDARY_POLICY.md) | Controller / Implementer boundary policy; the lease does not relax this boundary. |
| [`./NO_COPY_PASTE_PATTERN.md`](./NO_COPY_PASTE_PATTERN.md) | Pointer-only relay shape; lease records cite envelopes by path, never inline their content. |
| [`./PATH_MANIFEST_FIDELITY_PROTOCOL.md`](./PATH_MANIFEST_FIDELITY_PROTOCOL.md) | Manifest count/hash preflight; lease records are local-runtime and not subject to manifest fidelity. |
| `schemas/worktree-lease.schema.yaml` | Tracked machine-readable contract for lease records. |
| `schemas/active-work-ledger.schema.yaml` | Tracked machine-readable contract for ledger records (unchanged by Slice 2A). |

Where this protocol overlaps with the Feature 002 verifies-not-ratifies
invariant or with the Feature 001 author/approver separation contract,
the upstream contract controls. This protocol adds an intent-to-write
substrate layer above the Active-Work Ledger; it does not redefine
those contracts and it does not bump the Active-Work Ledger schema
version.

## c. Scope of Slice 2A

Slice 2A is **record / validate / refuse only**:

* defines the tracked Worktree Lease record schema;
* documents the untracked local runtime directory shape under
  `.hermes/active-work-ledger/leases/`;
* validates one lease record at a time via the new
  `worktree_lease_schema` check (`PCO-020`);
* additively extends `active_work_ledger_conflicts` with two new
  refusal predicates (`PCO-021`, `PCO-022`) plus a structural
  pre-validation code (`PCO-023`);
* gates those additive predicates on the discovery of at least one
  valid lease record in the scanned tree, so trees with zero lease
  records preserve Slice 1/2 behavior unchanged.

Slice 2A does **not**:

* allocate worktrees;
* mutate `git worktree` state in any way;
* create, delete, or rename branches;
* ship a `pco-allocate` / `pco-release` CLI;
* introduce a Hermes runtime hook;
* launch panes;
* re-enable `pco-completion-gate`;
* fully solve cryptographic controller-identity binding; PCO-024 (§j) adds Ed25519
  lease-signature substrate for `schema_version: "2"` leases, but full identity
  hardening (key issuance, key-trust enforcement) remains reserved for later workstreams;
* fold in public-launch readiness, dirty-root cleanup, pane registry,
  side-effect ledger, fan-in, or integration queue work.

Each later slice that closes a corresponding gap is named in §k.

## d. Tracked-schema vs local runtime-state distinction

* `schemas/worktree-lease.schema.yaml` is **tracked**. It is the
  canonical lease record contract, frozen at the commit level, and
  reviewed through the normal Source-ratified mutation flow.
* Lease records are **local runtime state**. They live under
  `.hermes/active-work-ledger/leases/`, which is covered by the
  existing `.hermes/` ignore rule, and they MUST NOT be added to the
  index. Adding them would conflate runtime state with substrate.
* This protocol document, the tracked schema, the new validator
  check, the additive predicates, the bundled examples, and the
  tests are tracked.

## e. Runtime directory shape

The lease record runtime directory layout is:

```
.hermes/active-work-ledger/
  leases/<controller-id>/<lease-id>.yaml
```

* `leases/<controller-id>/<lease-id>.yaml` — one lease record per
  `(controller_id, lease_id)` pair. Overwritten on lease renewal or
  expiry. A Controller MAY hold multiple concurrent leases for
  different worktrees by emitting multiple lease files under the
  same `<controller-id>` directory; each `<lease-id>` is the file
  basename so that the lease layer is structurally sibling to the
  Slice 0 `claims/`, `heartbeats/`, and `events/` directories.

Orphaned atomic-write temporary files of the form
`<target>.tmp.<pid>.<nonce>` MAY appear under `leases/`. The
validator MUST tolerate them by skipping (see §g), mirroring the
Slice 0 ledger discipline.

The lease layer is structurally sibling to the Slice 0 ledger
directories. It is NOT a child of `claims/` and it is NOT a child of
`events/`. The lease layer is its own coordination primitive.

## f. Lease record fields

A lease record (`record_type: worktree_lease`) carries:

* `kind: worktree-lease-record` (discriminator).
* `record_type: worktree_lease`.
* `schema_version: "1"`.
* `controller_id` — same shape and same caveats as in the
  Active-Work Ledger; pattern `^[a-z][a-z0-9-]{2,63}$`.
* `lane_id` — pattern `^[a-z][a-z0-9-]{2,63}$`. The lane the
  Controller intends to claim under this lease. Lease coverage is
  keyed by `(controller_id, worktree_path)`, **not** by `lane_id`;
  lane uniqueness remains owned by the Slice 1/2
  `active_work_ledger_conflicts` `PCO-016` predicate.
* `record_timestamp` — ISO-8601 UTC `Z` or source-controlled
  reference, same shape as `schemas/active-work-ledger.schema.yaml`.
* `lease_id` — required; matches pattern `^[a-z0-9][a-z0-9-]{2,63}$`.
  Stable within `(controller_id, lane_id, YYYY-MM-DD)` scope.
* `worktree_path` — required; repo-relative or absolute path of the
  physical worktree the lease intends to claim. Treated as advisory,
  not a secret. The `worktree_path` is the primary contention key.
* `acquired_at` — required timestamp at which the lease was
  acquired. Same shape as `record_timestamp`.
* `lease_seconds` — required integer in `[60, 86400]`. Default is
  `3600` (one hour); the schema validates the range only.
* `expires_at` — required timestamp at which the lease expires. A
  lease whose `expires_at` is in the past is considered expired and
  no longer covers a claim under `PCO-021` (see §i).
* `pane_label` — optional; one of
  `architect | implementer | controller | reviewer`. Generic role
  label only. NOT a model or tool binding.
* `branch` — optional; branch name the lease intends to operate on.
* `envelope_ref` — optional; repo-relative path to the active
  Assignment Envelope, or the literal `none` for coordination lanes
  without an envelope.
* `note` — optional free-text status note, `maxLength: 1024`. MUST
  NOT contain secrets, tokens, credentials, or actor ids. Slice 2A
  does not enforce this prohibition mechanically.

## g. Atomic-write and advisory-lock discipline (documentary)

This protocol documents the same atomic-write and advisory-lock
disciplines that govern the Slice 0 ledger. They are **documentary in
Slice 2A**: enforcement is the Slice 2R runtime allocator's concern.

Writers SHOULD:

1. Write the new lease record to
   `<target>.tmp.<pid>.<nonce>` within the same directory as
   `<target>`.
2. `fsync(2)` the temp file.
3. `rename(2)` it over `<target>` atomically.
4. Hold an exclusive advisory `flock(LOCK_EX)` on
   `.hermes/active-work-ledger/locks/<lane-id>.lock` around every
   read-modify-write sequence touching that lane's lease, claim, or
   heartbeat files.

The validator MUST tolerate orphaned `*.tmp.*` lease files by skipping
them; a stale temp file is not a validation failure.

## h. Lease lifecycle semantics

* A lease is **live** when `now < expires_at`. When `expires_at`
  resolves to a source-controlled or commit-based reference (not a
  wall-clock UTC timestamp), the lease defaults to live for the
  purposes of the validator's lease-aware predicates, mirroring the
  ledger's stale-record advisory posture for non-wall-clock
  timestamps.
* A lease is **expired** when `now >= expires_at`. Expired leases
  no longer cover claims under `PCO-021`.
* A Controller MAY renew a lease by writing a new record with the
  same `lease_id` and a fresh `acquired_at` + `expires_at`. Renewal
  is operationally optional in Slice 2A; no validator predicate
  forces it.
* A Controller SHOULD remove its own lease file when the lease is no
  longer needed (claim completed, lane abandoned). Cleanup is also
  operationally optional in Slice 2A; an expired lease is mechanically
  indistinguishable from a removed lease.

## i. Claim ↔ lease coverage semantics

A live ledger claim (one whose `last_heartbeat_at + lease_seconds`
has not elapsed and that has not been released) is **covered** by a
lease when both of the following hold:

1. There exists a live lease record in the scanned tree;
2. That lease's `controller_id` equals the claim's `controller_id`,
   and its normalized `worktree_path` equals the claim's normalized
   `worktree_path`.

Slice 2A enforces this coverage relationship via the additive
`active_work_ledger_conflicts` predicates:

* **`PCO-021` — `claim_requires_live_lease`**: a live claim whose
  worktree is not covered by a live lease under the same
  `controller_id` is refused. Gated on the discovery of at least one
  valid `worktree_lease` record in the scanned tree.
* **`PCO-022` — `worktree_lease_conflict`**: two live leases for the
  same normalized `worktree_path` under *different* `controller_id`
  values is itself a refusal. This is the contention-resolution
  predicate; it refuses cross-controller worktree races *before*
  either side writes a ledger claim.
* **`PCO-023` — `worktree_lease_invalid_record`**: a structurally
  invalid lease record discovered during the conflict scan surfaces
  separately from `PCO-020` so the schema-validity surface is not
  silently widened. Resolve `PCO-020` first.

The Slice 1/2 worktree-collision predicate (`PCO-010`) remains in
force: even when leases are present, two live ledger claims on the
same worktree under different controllers still fail `PCO-010`. The
lease layer is an *additional* refusal surface, not a replacement.

The lease layer's `controller_id` matching is exact-string. Lane
matching is intentionally **not** required: a single lease MAY cover
multiple lanes a Controller drives in the same worktree (e.g., an
architect lane and an implementer lane on the same physical
worktree). Lane uniqueness across live claims remains owned by
Slice 1/2 `PCO-016`.

## j. PCO-024 Lease signature substrate (Slice 2.5B)

PCO-024 extends the worktree-lease record with an optional
`worktree_lease_signature` field that binds the lease to a landed
controller-key record (`PCO-025`). A signed lease carries
`schema_version: "2"`; unsigned v1 leases remain valid.

### Signature record shape

```yaml
worktree_lease_signature:
  algorithm: ed25519
  canonicalization: creator-engine/worktree-lease-signature/v1
  key_ref: tenants/<tenant>/controllers/<controller-id>.key.yaml
  value: <unpadded base64url Ed25519 signature bytes>
```

### Signing payload

The payload is the canonical UTF-8 JSON encoding of the lease record
**with `worktree_lease_signature` removed**: compact separators
(`","` / `":"`), keys sorted lexicographically (RFC 8785 spirit).

```
canonicalization: creator-engine/worktree-lease-signature/v1
payload = json.dumps({k: v for k, v in record.items()
                      if k != "worktree_lease_signature"},
                     sort_keys=True, separators=(",", ":")).encode("utf-8")
```

### PCO-024 refusal predicates

The `worktree_lease_schema` check (`PCO-020`) additionally enforces
`PCO-024` for signed leases:

* **malformed signature bytes** — value is not valid unpadded
  base64url, or decodes to other than 64 bytes.
* **missing / unknown controller-key** — `key_ref` does not resolve
  to a discovered `controller-key-record` in the scanned tree.
* **revoked controller-key** — resolved key has `status: revoked`.
* **key_ref / controller_id binding mismatch** — the controller-key
  record's `controller_id` does not match the lease's `controller_id`.
* **signature verification failure** — Ed25519 signature verification
  against the resolved public key fails.

Schema errors (v2 lease missing the field, or v1 lease carrying it)
still surface as `PCO-020`.

### Private-key prohibition

The controller private key MUST NOT enter worker containers.
PCO-024 is substrate-only: it validates signatures using landed public
keys; it does not generate, inspect, store, or log private keys or
real credentials.

## k. Controller-identity caveat (pre-PCO-024)

Unsigned v1 lease records are only as trustworthy as the
`controller_id` that claims them. For signed v2 leases, the
controller-key substrate (`PCO-025`, `PCO-024`) binds the lease to
a Source-ratified per-host keypair.

In multi-Controller rehearsals the Controller boundary policy
([`./CONTROLLER_BOUNDARY_POLICY.md`](./CONTROLLER_BOUNDARY_POLICY.md))
and Source ratification continue to apply. The lease layer is a
coordination primitive; PCO-024 adds a signature verification
layer but does not replace Source ratification.

## l. Relationship to future slices

* **Slice 2R — Worktree Allocator Runtime**: ships `pco-allocate` /
  `pco-release` CLI, `git worktree` binding, advisory lease lock,
  and claim-writes-only-under-held-lease enforcement. Slice 2A is
  the substrate Slice 2R operates on.
* **Slice 2.5 — Controller Identity Substrate** *(provisional)*:
  hardens `controller_id` against forgery (per-host keying, signing
  surface, etc.). Slice 2A explicitly defers this.
* **Slice 3 — Pane Registry**: binds visible Architect/Implementer
  panes to specific claims. Slice 2A leaves `pane_label` as a
  generic role hint only.
* **Slice 4 — Side-Effect Ledger**: tracks externally observable
  side effects per lane. Depends on a stable lane substrate (Slice 0)
  and on resolved worktree-contention semantics (Slice 2A / 2R).
* **Slice 5 — `pco-fanin`**: integration verification under
  multi-lane authorship; explicitly does not trust lane self-report.
* **Slice 6 — Integration Queue**: serialized canonical-branch
  landing order across lanes.

Each slice keeps the substrate-before-automation discipline: protocol
and validator first, runtime tooling after.

## m. Slice 2A / PCO-024 boundary statement

**Slice 2A records, validates, and refuses Worktree Lease state; it
does NOT yet allocate worktrees, does NOT mutate `git worktree`
state, does NOT ship a `pco-allocate` / `pco-release` CLI, does NOT
re-enable `pco-completion-gate`, and does NOT solve cryptographic
controller-identity binding. Runtime allocation is reserved for
Slice 2R. Identity hardening is reserved for a separately ratified
follow-on workstream.**

PCO-024 (§j, Slice 2.5B) adds Ed25519 lease-signature verification for
`schema_version: "2"` leases within this substrate. The "does NOT solve
cryptographic controller-identity binding" clause in the statement above
refers to full identity hardening (per-host key issuance, key-trust
enforcement); PCO-024 provides the verification layer, not the issuance
or trust-root layer. That narrower reading is consistent with the
statement; the normative text is preserved verbatim.

This statement is normative. Reviewers MUST see it preserved
verbatim in this document, in the schema description, in
[`../architecture/parallel-controller-orchestration.md`](../architecture/parallel-controller-orchestration.md),
and in
[`../../specs/005-pco-parallel-controller-orchestration/spec.md`](../../specs/005-pco-parallel-controller-orchestration/spec.md).

## n. Prohibited surfaces

Lease records MUST NOT carry:

* secrets, tokens, credentials, source-host installation ids;
* durable actor ids, app slugs, account names;
* concrete model, tool, CLI, runner, or QA-harness identifiers as
  normative upstream bindings;
* machine-local absolute paths beyond `worktree_path` (which is
  required and treated as advisory, not as a secret).

This prohibition mirrors the Slice 0 ledger schema prohibition.
Slice 2A does not enforce it mechanically beyond the schema's
structural constraints (`unevaluatedProperties: false`, enum on
`pane_label`); the broader discipline is operational.

## o. Acceptance posture

A fresh-clone reviewer can verify the following from this document
alone:

1. What a Worktree Lease record is and what it is for.
2. The untracked runtime directory shape under
   `.hermes/active-work-ledger/leases/` and why it is untracked.
3. The lease record fields, the lease lifecycle semantics, and the
   `expires_at` expiry rule.
4. The atomic-write and advisory-lock disciplines (documentary in
   Slice 2A; runtime tooling is later-slice scope).
5. The claim ↔ lease coverage relationship and the three additive
   refusal predicates (`PCO-021`, `PCO-022`, `PCO-023`).
6. The backward-compatibility gate: trees with zero lease records
   preserve Slice 1/2 behavior unchanged.
7. The controller-identity caveat and which workstream is responsible
   for hardening it.
8. The Slice 2A boundary statement (§l) and the future-slice
   sequence that closes each deferred gap.
