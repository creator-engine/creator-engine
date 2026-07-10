---
kind: decision-record
record_type: adr
schema_version: "1"
id: ADR-0015-materializer-arming-credential-lease
title: "Materializer arming authority, credential custody, and lease topology"
status: proposed
date: "2026-07-10"
decision_makers: ["ce-dev-2"]
# ratification:             # REQUIRED once status: accepted; ratifier = Operator (independent of decision_makers per security mutation_class)
#   ratified_by: "<operator-handle>"
#   ratified_at: "YYYY-MM-DD"
#   ratification_prompt_sha: "<64-hex>"
consulted: []
informed: []
review_by: "2026-10-10"
mutation_class: security
evidence_refs:
  - kind: doc
    ref: "docs/design/ce-491-optiona-merge-intent.md"
    tag: merge-intent-design
  - kind: doc
    ref: "tools/egress-broker/egress_broker/minter.py"
    tag: vault-signer-impl
  - kind: doc
    ref: "docs/devops/openbao/openbao-secret-path-map.tsv"
    tag: openbao-path-map
  - kind: doc
    ref: "validators/creator_engine_validator/brain_intent_materializer.py"
    tag: materializer-impl
crosswalk:
  informs: []
---

# Materializer arming authority, credential custody, and lease topology

## Context and Problem Statement

The merge-time brain append materializer design leaves several Operator
questions open before direct writes to `main` can be armed. The materializer
needs a narrow authority path, a credential form for the forge App private key,
and a lease topology that matches the first deployment shape without hiding the
multi-instance hazard.

## Decision Drivers

- Arming direct write authority must be explicit, reviewable, and auditable.
- Workers must not receive or persist forge App private key material.
- The first implementation should match the current single-host singleton
  topology while failing closed if that topology changes.
- The materializer must preserve the existing merge-gate singleton authority
  model and avoid a second policy gate.

## Considered Options

**Q1 — Arming Authority**

1. Governed PR with Operator co-sign artifact following the ratified
   release-signing model.
2. Runtime-only arming by local configuration, shell access, chat instruction,
   or ambient daemon state.

**Q2 — Credential Delivery Mechanism**

1. Per-call fetch via the vault_signer pattern already shipped for the egress
   broker: per-call OpenBao KV v2 read at the per-app private-key path →
   /dev/fd pipe to openssl signing subprocess; key never written to disk, never
   in worker env ([vault-signer-impl]).
2. Long-lived private key file, repository secret, environment variable, or
   host-local PEM exposed directly to the worker or daemon process.

**Q4 — Lease Topology**

1. Local file lease via MaterializerLease wrapping daemon_lease.acquire for
   the current single-host singleton topology ([materializer-impl]).
2. External linearizable lock required before first single-host arming.

## Decision Outcome

Chosen option: **governed arming with brokered short-lived credentials and a
local singleton lease for the current topology**.

### Q1: Arming Authority

Decision: arm the materializer only through a governed PR that flips the
arming constant, accompanied by an Operator co-sign artifact following the
ratified release-signing model.

Rationale: a tracked PR makes the arming change reviewable and keeps the code
constant in the normal governance path. The separate Operator co-sign artifact
records that the human authority to grant direct write capability exists outside
the worker-authored change. This preserves the merge-gate singleton model: the
daemon performs deterministic closeout, but the authority to arm direct `main`
writes is not inferred from implementation work.

Rejected alternative: runtime-only arming by local configuration, shell access,
chat instruction, or ambient daemon state. Those paths are not reviewable in the
repository and would let arming happen without the same durable evidence as the
release-signing flow.

Revisit trigger: revisit if the release-signing model is superseded, if the
arming constant is replaced by a ratified capability envelope, or if branch
protection no longer permits a path-scoped direct-write exception for the
materializer.

### Q2: Credential Form For The App Private Key

Decision: use OpenBao-backed short-TTL issuance for the dedicated materializer
App credential. The App private key must never be written to worker disk or
placed in worker-visible logs, prompts, argv, repository files, comments, or
evidence artifacts. The delivery mechanism is per-call fetch via the
vault_signer pattern already shipped for the egress broker ([vault-signer-impl]):
per-call OpenBao KV v2 read at the per-app private-key path → /dev/fd pipe to
openssl signing subprocess → JWT; the PEM is zeroed from memory after signing
and never written to disk or passed through any worker-visible env var or argv.
The materializer App private-key path follows the per-app family established in
the OpenBao secret-path map ([openbao-path-map]):
`ce-kv/forge/github-apps/<app-name>/private-key`; the concrete materializer-app
path is specified in the arming runbook (slice (c)), not in this ADR.

Rationale: the vault_signer pattern is the implemented precedent in
`tools/egress-broker/egress_broker/minter.py` ([vault-signer-impl]). It
provides audit-before-issue, narrow policy, TTL-bound grants, and revocation
without distributing standing private key material. Pinning delivery to the
same mechanism as the egress broker eliminates a design divergence and reuses
tested signing infrastructure.

Rejected alternative: a long-lived private key file, repository secret,
environment variable, or host-local PEM exposed directly to the worker or daemon
process. Those forms are harder to revoke, harder to audit per use, and easier
to leak through tooling, crash dumps, logs, or prompts.

Revisit trigger: revisit if OpenBao is replaced as the default secret backend,
if forge support allows a narrower non-PEM dynamic credential, or if live
operations prove that the vault_signer pattern cannot perform the direct commit
without raw key material entering the worker lane.

### Q4: Lease Topology

Decision: for the current single-host, strict singleton merge-gate daemon
topology, use MaterializerLease wrapping daemon_lease.acquire("brain-append",
...) in `validators/creator_engine_validator/brain_intent_materializer.py`
([materializer-impl]) as the active exclusion mechanism for the `brain-append`
component. This local file lease is authoritative for the current single-host
topology. The revisit trigger is any second host or instance gaining
brain-append capability.

Rationale: under the current topology there is exactly one materializer
execution locus, so the local lease gives crash recovery, operator diagnostics,
and accidental re-entry protection without introducing another distributed
service into the first arming slice. The design already identifies the safety
boundary: once more than one instance can materialize, a local file cannot prove
linearizable exclusion across hosts or processes.

Rejected alternative: require an external linearizable lock before the first
single-host arming. That would solve the future multi-instance case but add a
new availability and operations dependency before it is needed for the current
topology.

Revisit trigger: require a new decision and implementation gate before any actor
other than the strict singleton daemon gains brain-append capability, before
running two materializer instances, before moving the materializer off the
singleton host, before adding active-active failover, or before sharing the same
append ledger across hosts.

## Consequences

- Good: direct write arming has both code-review evidence and Operator
  authority evidence.
- Good: App credential custody remains short-lived, auditable, and outside
  worker disk, delivered via the vault_signer mechanism already proven in the
  egress broker.
- Good: the first deployment avoids unnecessary distributed locking while
  naming the exact point where that choice stops being safe.
- Trade-off: the local lease decision is topology-bound and cannot be reused for
  high-availability or multi-instance materialization.
- Trade-off: live arming remains blocked until the governed PR, Operator
  co-sign artifact, and OpenBao-backed vault_signer issuance path exist.
