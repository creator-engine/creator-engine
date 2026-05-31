# ADR-V2-005: Federated identity binding + distributed claim substrate

## Status

Accepted for G2.004.2 draft substrate.

## Context

Creator Engine v2's team-mode / multi-repo control plane needs two coordination
record families before any distributed runtime exists: a way to assert that a
principal in one repository is the same principal across other repositories
(federated identity binding), and a cross-repo coordination claim primitive that
is the distributed analogue of a single-repo PCL `lane_claim` (distributed
claim). These must preserve the Operator-only privileged floor, support
operating-mode context, reference CE-event blocks and PCL records without
coupling to them, and avoid creating premature key custody or distributed
runtime obligations.

## Decision

G2.004.2 defines both families as content-addressed, hash-chained records
discriminated by `record_kind`, with a shape-only signature field — mirroring the
G2.004.0 PCL record substrate. The gate ships docs, two schemas, validator
checks (`federated_identity_binding`, `distributed_claim`), examples, tests, and
the spec/sidecar/ADR extension only.

A federated identity binding binds an opaque `principal_id` across at least two
repositories using opaque `repo_id` / `identity_ref` values; a
`binding_revocation` references the revoked binding by opaque hash. A distributed
claim binds to a federated identity binding by an opaque 64-hex `binding_ref` and
may reference CE-event blocks and PCL records only by opaque 64-hex content
hashes carried in the body. Because the substrate imports no federated-identity,
CE-event, or PCL code/schema, it carries no runtime dependency on G2.003.1 or
G2.004.1 — this decoupling is what lets G2.004.2 be authored in parallel with the
CE-event runtime gate G2.003.1 while depending only on the merged G2.004.0.

Both families are read-only coordination state and never ratify anything;
`agent_ratifier` stays reserved-inactive and cannot emit. The signature field is
present so later gates can bind real signing and key verification without
changing the base record shape.

G2.004.2 does not implement any runtime, `.ce/` live writes, signing, key
custody, federated identity runtime, distributed claim runtime, queue/connector
runtime, live record emission, GitHub settings, CI hooks, or deploy hooks. The
PCL runtime gate G2.004.1 (which depends on both G2.004.0 and G2.003.1) and the
federated-identity / distributed-claim runtime remain separate, deferred,
Operator-ratified gates.

## Consequences

- Draft PR authoring proceeds in parallel with G2.003.1 because this gate is a
  layer-2 substrate composed of mostly new files.
- The only known shared append surface is the validator check registry import in
  `validators/creator_engine_validator/checks/__init__.py`; G2.003.1 does not
  edit the feature-004 record families, so any landing conflict there is
  serialized PR fan-in work.
- Merge readiness remains a separate Operator-ratified review/approval/merge
  workflow; canonical-branch integration is serialized with G2.003.1.
- Future runtime gates can depend on stable federated-identity and
  distributed-claim record shapes without retrofitting coordination metadata.

## Non-ratification statement

This ADR records a design decision for the PR candidate. It ratifies no future
runtime authority, no privileged-floor relaxation, and no agent ratification.
