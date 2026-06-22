---
kind: decision-record
record_type: adr
schema_version: "1"
id: ADR-0012-openbao-micro-unit-standup
title: "OpenBao micro-unit stand-up design"
status: proposed
date: "2026-06-22"
decision_makers: [ce-dev-4]
consulted: [ce-ops#135, ce-ops#113]
informed: []
review_by: "2026-09-22"
mutation_class: security
evidence_refs:
  - kind: issue
    ref: "https://github.com/creator-engine/ce-ops/issues/135"
    tag: ce-ops-135
  - kind: issue
    ref: "https://github.com/creator-engine/ce-ops/issues/113"
    tag: ce-ops-113
  - kind: doc
    ref: "docs/decisions/0005-openbao-secret-identity-backend.md"
    tag: adr-0005
  - kind: doc
    ref: "docs/contracts/openbao-secret-zero-broker.md"
    tag: secret-zero-contract
  - kind: web
    ref: "https://openbao.org/docs/"
    tag: openbao-docs-25x
  - kind: web
    ref: "https://openbao.org/docs/auth/approle/"
    tag: openbao-approle
  - kind: web
    ref: "https://openbao.org/docs/concepts/response-wrapping/"
    tag: openbao-response-wrapping
  - kind: web
    ref: "https://openbao.org/docs/secrets/kv/kv-v2/"
    tag: openbao-kv-v2
  - kind: web
    ref: "https://openbao.org/docs/secrets/ssh/"
    tag: openbao-ssh
  - kind: web
    ref: "https://openbao.org/docs/secrets/ssh/signed-ssh-certificates/"
    tag: openbao-ssh-signed-certificates
  - kind: web
    ref: "https://openbao.org/api-docs/secret/ssh/"
    tag: openbao-ssh-api
  - kind: web
    ref: "https://openbao.org/docs/secrets/transit/"
    tag: openbao-transit
  - kind: web
    ref: "https://openbao.org/docs/audit/"
    tag: openbao-audit
  - kind: web
    ref: "https://openbao.org/docs/concepts/seal/"
    tag: openbao-seal
  - kind: web
    ref: "https://openbao.org/docs/concepts/ha/"
    tag: openbao-ha
  - kind: web
    ref: "https://openbao.org/docs/configuration/storage/raft/"
    tag: openbao-raft
  - kind: web
    ref: "https://openbao.org/docs/agent-and-proxy/agent/"
    tag: openbao-agent
policy_sha: "5d17b74a35303285ab923c83010f58db12d098b85200ba4b6fbc1eb356e55e2b"
crosswalk:
  informs:
    - ce-ops#135
    - ce-ops#113
---

# OpenBao micro-unit stand-up design

## Context and Problem Statement

ADR-0005 selected OpenBao behind `SecretIdentityBackend`, and the secret-zero
broker contract now defines response-wrapped AppRole delivery for per-dev
machine seats. The remaining ce-ops#135 question is the deployment shape for a
dedicated secret-store micro-unit that can start small without losing the path
to production isolation, HA, auditability, and environment separation.

This ADR is design-only. It does not authorize live OpenBao stand-up, live
secret migration, root-token handling, unseal custody, caller wiring, or
production deployment.

## Decision Drivers

- Keep CE callers backend-agnostic through the existing `SecretIdentityBackend`
  seam from ADR-0005.
- Separate dev/test/prod secret planes so non-production seats cannot reach
  production identities or audit streams.
- Prefer a single-node development start that can graduate to a three-node HA
  micro-unit without changing caller contracts.
- Use machine-appropriate auth for governed seats and brokers.
- Preserve value-free records: no secret values in git, logs, PR bodies,
  tickets, tmux panes, or LLM-visible evidence.
- Require audit availability before issuing grants.

## Considered Options

1. Dedicated OpenBao micro-unit per environment, starting with single-node dev
   and graduating to HA integrated-storage clusters.
2. Shared multi-environment OpenBao instance with path/policy separation only.
3. Continue host-local files until production migration is ready.

## Decision Outcome

Chosen option: **dedicated OpenBao micro-unit per environment, single-node dev
first, HA path preserved**.

The dev profile may use one OpenBao node on a broker-only network with
integrated storage, file audit, Shamir unseal, and no live production secrets.
The HA profile promotes each environment to its own three-node OpenBao cluster
with integrated storage/Raft, TLS-only API and cluster addresses, one active
node plus standbys, tested snapshots/restores, and independent audit sinks.
The `SecretIdentityBackend` API remains the caller boundary for both profiles.

## Topology

| Environment | Stand-up profile | Storage and HA path | Boundary |
| --- | --- | --- | --- |
| `dev` | Single node, disposable or rebuildable, broker-network-only. | Integrated storage on one node; tested restore before any real secret import. | Dev-only KV/AppRole/SSH/Transit mounts and dev audit sink. |
| `test` | Single node or three-node HA rehearsal before production migration. | Same config shape as prod; may be reset from fixtures, never from prod snapshots. | Test-only identities and audit sink. |
| `prod` | Three-node HA micro-unit after Operator gate. | Integrated storage/Raft with quorum, TLS cluster traffic, backups, restore drills, and emergency seal runbook. | Prod-only identities, prod audit sink, no dev/test auth mounts. |

OpenBao 2.5.x docs show HA mode is multi-server and active/standby, and
integrated storage is the intended storage path for this design
([openbao-ha], [openbao-raft]). Single-node dev is a topology convenience only;
production readiness requires the HA profile and restore proof.

## Auth Method

Use AppRole for machine seats and broker-side components. Each concrete dev
seat gets a role named `ce-dev-N`, least-privilege policies, short token TTLs,
single-use SecretIDs, and response-wrapped delivery through the existing
secret-zero broker contract. Humans do not receive root tokens or raw broker
credentials through this path.

AppRole is VERIFIED in OpenBao 2.5.x docs as machine/app oriented auth with
RoleID and SecretID login ([openbao-approle]). Response wrapping is VERIFIED as
single-use wrapped response delivery using the `X-Vault-Wrap-TTL` request header
and unwrap/lookup/rewrap/wrap endpoints ([openbao-response-wrapping]).

## Secret Engines

| Engine or capability | Status | Use in this design | Source |
| --- | --- | --- | --- |
| KV v2 | VERIFIED, OpenBao 2.5.x | Store value-bearing identity material behind `SecretRef` pointers. Mount separately per environment, e.g. `ce-kv-dev`, `ce-kv-test`, `ce-kv-prod`. | [openbao-kv-v2] |
| Cubbyhole / response wrapping | VERIFIED, OpenBao 2.5.x | Deliver short-lived AppRole SecretIDs without persisting raw values in CE records. | [openbao-response-wrapping] |
| SSH secrets engine, signed certificates | VERIFIED, OpenBao 2.5.x | Broker root operations should generate an ephemeral keypair outside the LLM context and call `/ssh/sign/:role` with the public key. | [openbao-ssh], [openbao-ssh-signed-certificates], [openbao-ssh-api] |
| SSH secrets engine, issue endpoint | VERIFIED, OpenBao 2.5.x | Do not use for broker root ops by default because `/ssh/issue/:role` can return a generated private key and certificate to the caller. | [openbao-ssh-api] |
| Transit | VERIFIED, OpenBao 2.5.x | Use only if CE needs signing/encryption-as-a-service for broker-held values. Signing keys remain in Transit; decrypt responses can expose plaintext and must stay outside LLM-visible context. | [openbao-transit] |
| AppRole auth | VERIFIED, OpenBao 2.5.x | Machine auth for seats and broker components; one role per concrete seat or service identity. | [openbao-approle] |
| Agent auto-auth/template/cache | VERIFIED, OpenBao 2.5.x | Candidate for future non-LLM sidecar materialization, not wired by this ADR. | [openbao-agent] |
| Cloud IAM secret engines | ASSUMED-PENDING-VERIFICATION | Not part of this design. Do not claim AWS/GCP/Azure IAM engines are built in unless a later primary-source check verifies them. | none |

## Seal, Unseal, Audit, and Recovery

- Start dev/test with Shamir unseal under Operator custody; no unseal shares in
  git, CI secrets, issue comments, PRs, terminal transcripts, or LLM context.
- Production may move to auto-unseal only after a separate Operator decision
  accepts the lifecycle dependency on the seal provider and validates recovery
  controls.
- Enable at least one audit device before any grant issuance. The existing
  OpenBao backend already fails closed when audit preflight is unavailable.
- Audit sinks are environment-specific. Dev/test/prod audit logs must not share
  writable storage or retention controls.
- Backups and restore drills are mandatory before importing real credentials;
  prod restore evidence must be generated from prod-specific encrypted backups.
- Emergency seal is an Operator action, not a seat or caller action.

OpenBao 2.5.x docs verify the sealed startup state, Shamir unseal flow, auto
unseal trade-off, and seal operation ([openbao-seal]). Audit devices are
VERIFIED as detailed request/response logging for OpenBao API interactions,
with specific system exceptions ([openbao-audit]).

## Adapter Skeleton

The code seam already exists in
`validators/creator_engine_validator/secret_identity.py`: `SecretIdentityBackend`,
registry helpers, `FakeSecretIdentityBackend`, and `OpenBaoSecretIdentityBackend`
with injected runner/materializer/deliverer. W4 keeps that seam and adds only a
local compatibility backend for existing host-local references. Future callers
should depend on the protocol and registry, not on OpenBao-specific classes.

The OpenBao adapter remains injected-I/O only in unit tests. No live OpenBao
server is started by this ADR.

## Consequences

- Good: CE gets a concrete micro-unit design that composes with the existing
  backend seam and secret-zero broker.
- Good: Dev can start with a small topology while prod retains a direct HA path.
- Good: Environment separation is a precondition, not a cleanup task after
  migration.
- Bad: Production migration remains blocked until Operator-held deployment,
  unseal, backup, restore, audit, and emergency procedures are proven.
- Bad: Operating OpenBao adds service ownership, patching, monitoring, and
  recovery duties.
- Bad: Transit decrypt and SSH issue endpoints can return plaintext/private
  material, so CE must keep them out of LLM-visible and persistent records.

## Non-Ratification Statement

This ADR is proposed design evidence only. It does not ratify live OpenBao
deployment, live server start, production init, unseal/recovery custody,
root-token handling, live secret migration, runtime caller wiring, or use of
OpenBao to hold governance signing roots.
