# Credential Identity Architecture Findings

**Record status:** findings only. This point-in-time architecture record does
not authorize credential movement, OpenBao deployment, broker arming, token
issuance, policy binding, approval, merge, signing, or any runtime act.

## Product Lens

Creator Engine needs an identity plane that lets product workflows make
bounded, auditable actions without giving a person or workload a standing
credential. The current direction has useful containment controls and a
credential backend interface, but it is not yet a complete workload-identity
system. The near-term product outcome is reduced exposure from legacy
per-seat write credentials; the longer-term outcome is verifiable,
short-lived identity for each permitted action.

## Evidence Anchors

The following tracked-source anchors support the findings in this record.
They describe design and implementation evidence, not live operation.

- Credential migration inventory: `docs/devops/openbao/secret-migration-inventory.tsv:2-5,7-14`.
- Legacy credential lookup and child-process injection boundary:
  `validators/creator_engine_validator/ce_cli.py:2154-2160,5335-5343`.
- Backend direction and unratified operating boundaries:
  `docs/decisions/0005-openbao-secret-identity-backend.md:113-120,141-146`.
- One-use bootstrap and memory-only session contract:
  `docs/contracts/openbao-secret-zero-broker.md:9-37,49-70`.
- Scoped, revocable issuance design that is not wired as a live path:
  `docs/architecture/egress-broker.md:1-5,49-67,98-110`.
- Credential-carrier protections at the execution boundary:
  `validators/creator_engine_validator/codex_launch_spec.py:48-94,294-337` and
  `deploy/dgx-runsc/README.md:177-189,383-401`.
- Per-call signing and legacy fallback behavior:
  `tools/egress-broker/egress_broker/config.py:61-75,216-233` and
  `tools/egress-broker/egress_broker/minter.py:23-28,209-222,302-320`.

## Identity Scorecard

| Enterprise identity-plane property | Score | Finding |
| --- | --- | --- |
| Central identity and secret plane | PARTIAL | A backend direction and value-free interfaces exist; no production deployment or completed migration is evidenced. |
| OIDC federation | MISSING | No tracked issuer, trust configuration, claims mapping, or federated workload flow is evidenced. |
| SPIFFE/SVID workload identity and attestation | MISSING | No trust domain, workload API, attestor, SVID lifecycle, or verifier is tracked. |
| Per-action, short-lived issuance | PARTIAL | The broker design can mint scoped, revocable installation tokens, but the live path is explicitly unwired. |
| No actor-held standing credential | PARTIAL | Execution-boundary protections are strong, while legacy per-seat write credentials and signing fallbacks remain. |
| Policy outside the actor | PARTIAL | Broker policy, envelope checks, and launch validation are externalized, but not yet a universal runtime policy decision and enforcement point. |
| Dynamic secrets, rotation, and revocation | MISSING | Current backend use is principally static custody plus bootstrap; no dynamic secret engine or automated lifecycle is demonstrated. |
| Auditing and incident evidence | PARTIAL | Audit and recovery prerequisites are designed, with no tracked production evidence of operation. |

The record therefore has three MISSING and five PARTIAL properties. The larger
gap is federated, attested workload identity with dynamic issuance; host-local
custody of standing credentials is the highest immediate exposure within that
gap.

## Threat Framing

- A legacy per-seat write credential can be replayed by a process that obtains
  its host-local custody material.
- A signing credential can mint installation tokens; compromise carries the
  scope of the installation until revocation.
- Bootstrap material or a backend client token carries the policy domain of its
  role. One-use wrapping reduces exposure but is not workload attestation.
- Governance and backend recovery roots are operator-level roots and must stay
  separate from normal runtime custody.
- Review and bootstrap credentials can influence protected actions; authority
  envelopes constrain actions but do not replace identity.

## Conditional Containment Verdict

**Verdict: MOVE-WITH-CONDITIONS.** Moving an affected legacy per-seat write
credential from controller-readable home custody to root-only broker custody is
an exposure reduction only. It is not a central identity-plane implementation
and must not be treated as completion of the dynamic-identity roadmap.

The move is appropriate only after all seven gates pass:

1. Inventory actual consumers and prove that no service, launcher, or recovery
   flow requires a direct file read.
2. Replace the legacy direct fallback for the affected write path with a
   deterministic host broker that receives value-free requests only.
3. Demonstrate broker policy binding to actor context, repository, action,
   permission ceiling, time-to-live, rate limit, and audited revocation.
4. Demonstrate that execution containers receive neither credential values nor
   credential-bearing environment or file carriers.
5. Prove failure-closed behavior for an unavailable broker, expired token,
   policy mismatch, and attempted direct fallback.
6. Rotate and revoke the original credential during an approved change window,
   retaining value-free evidence.
7. Obtain operator ratification and a tested recovery procedure.

## Product Roadmap

The work separates into four product categories:

1. **Containment prerequisites:** strengthen credentialless execution and
   worker identity binding. These controls reduce exposure but do not issue
   identity.
2. **Broker-only delivery:** complete per-user bootstrap policy, remove direct
   write-credential fallback, migrate signing custody to the backend, and
   require broker-only delivery.
3. **Federated workload identity:** define an OIDC issuer, claims-to-policy
   mapping, audiences, time-to-live, revocation semantics, a SPIFFE trust
   domain, workload attestation, SVID rotation, selector policy, and broker
   verification.
4. **Dynamic lifecycle:** replace static runtime-secret reads with leased
   credentials, explicit rotation ownership, revocation drills, and expiry
   telemetry; preserve authoritative identity, registry, and recovery-state
   continuity.

## Explicit Unknowns

This record did not inspect live credential files, service environments, file
permissions, credential scopes or expiry, backend deployment state, audit
receipts, or forge state. It cannot assert current production custody or whether
any migration is already operational. A separate review must confirm that this
redacted record remains faithful to its evidence before it is used as planning
input.
