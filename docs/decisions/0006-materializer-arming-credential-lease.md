---
kind: decision-record
record_type: adr
schema_version: "1"
id: ADR-0006-materializer-arming-credential-lease
title: "Materializer arming authority, credential custody, and lease topology"
status: proposed
date: "2026-07-10"
decision_makers: ["materializer-prearming-worker"]
consulted: []
informed: []
review_by: "2026-10-10"
mutation_class: security
evidence_refs:
  - kind: doc
    ref: "docs/design/ce-491-optiona-merge-intent.md"
    tag: merge-intent-design
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
evidence artifacts.

Rationale: OpenBao-backed issuance aligns with the existing secret custody
direction: audit before issue, narrow policy, TTL-bound grants, and revocation
without distributing standing private key material to workers. The materializer
should receive only the minimum runtime capability needed to perform the
bounded direct commit, preferably through a broker or sidecar trust boundary
that prevents raw key material from entering the worker lane.

Rejected alternative: a long-lived private key file, repository secret,
environment variable, or host-local PEM exposed directly to the worker or daemon
process. Those forms are harder to revoke, harder to audit per use, and easier
to leak through tooling, crash dumps, logs, or prompts.

Revisit trigger: revisit if OpenBao is replaced as the default secret backend,
if forge support allows a narrower non-PEM dynamic credential, or if live
operations prove that the broker or sidecar cannot perform the direct commit
without exposing raw key material.

### Q4: Lease Topology

Decision: for the current single-host, strict singleton merge-gate daemon
topology, use the local file lease described by the design as the active
exclusion mechanism for the `brain-append` component. Treat that lease as
insufficient for any multi-instance topology.

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

Revisit trigger: require a new decision and implementation gate before running
two materializer instances, moving the materializer off the singleton host,
adding active-active failover, sharing the same append ledger across hosts, or
allowing any actor other than the strict singleton daemon to materialize the
same component.

## Consequences

- Good: direct write arming has both code-review evidence and Operator
  authority evidence.
- Good: App credential custody remains short-lived, auditable, and outside
  worker disk.
- Good: the first deployment avoids unnecessary distributed locking while
  naming the exact point where that choice stops being safe.
- Trade-off: the local lease decision is topology-bound and cannot be reused for
  high-availability or multi-instance materialization.
- Trade-off: live arming remains blocked until the governed PR, Operator
  co-sign artifact, and OpenBao-backed issuance path exist.
