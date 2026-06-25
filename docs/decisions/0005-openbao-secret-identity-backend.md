---
kind: decision-record
record_type: adr
schema_version: "1"
id: ADR-0005-openbao-secret-identity-backend
title: "OpenBao-backed SecretIdentityBackend"
status: accepted
date: "2026-06-19"
decision_makers: [dev-1]
consulted: [ce-ops#113, chmod735]
informed: []
review_by: "2026-09-19"
mutation_class: security
evidence_refs:
  - kind: issue
    ref: "https://github.com/creator-engine/ce-ops/issues/113"
    tag: ce-ops-113
  - kind: doc
    ref: ".ce/state/research/DESIGN_ce113_openbao_20260619T031542Z.md"
    tag: design
  - kind: doc
    ref: "/home/ce/dev1-addenda-task.md"
    tag: ratification-addendum
  - kind: web
    ref: "https://openbao.org/community/release-notes/2-5-0/"
    tag: openbao-release-state
  - kind: web
    ref: "https://openbao.org/api-docs/"
    tag: openbao-http-api
  - kind: web
    ref: "https://openbao.org/api-docs/libraries/"
    tag: openbao-vault-compat
  - kind: web
    ref: "https://openbao.org/docs/auth/approle/"
    tag: openbao-approle
  - kind: web
    ref: "https://openbao.org/docs/auth/jwt/"
    tag: openbao-jwt-oidc
  - kind: web
    ref: "https://openbao.org/docs/audit/"
    tag: openbao-audit
policy_sha: "8b04004df48e8cec68d9bf5a4adbfd08222d0ca02dc0b2b08e873da7195c2d8f"
ratification:
  ratified_by: chmod735
  ratified_at: "2026-06-19"
  ratification_prompt_sha: "8b04004df48e8cec68d9bf5a4adbfd08222d0ca02dc0b2b08e873da7195c2d8f"
  # N=1 native mode: ratified by the sole resolved human (chmod735 -> peer-operator
  # in .ce/coordination.yml's identity_map). Honest solo quorum, NOT two-account
  # laundering. Auto-expires the instant the identity map resolves a second human.
  quorum: n1_solo
crosswalk:
  informs:
    - ce-ops#113
---

# OpenBao-backed SecretIdentityBackend

## Context and Problem Statement

CE now runs a growing fleet of dev and reviewer seats with unique identities.
The retired shared-author credential pattern cannot support that model. Current
secrets are scattered across host-local paths such as `~/.ce-keys`,
`~/.hermes/.env`, per-host GitHub App PEMs, reviewer tokens, and bootstrap
tokens. That blocks portable containerized seats, per-dev identity custody, and
the ce-ops#117 shared-App waitlist path because users must not receive the
shared App private key ([ce-ops-113], [design]).

## Decision Drivers

- CE needs a central, governed secret store for per-dev identities and App
  custody.
- Secret values must never appear in argv, tmux, evidence, ledgers, tracked
  records, issue comments, or PR bodies.
- Runtime credentials must be short-lived, least-privilege, auditable, and
  revoked on release.
- The default backend must avoid HashiCorp BUSL lock-in while preserving a
  Vault-compatible API profile.
- The implementation must keep CE's seams small: one adapter, no scattered
  provider calls.
- Deployment, unseal, backup, and migration require separate Operator gates;
  this decision accepts the backend/interface direction only.

## Considered Options

1. OpenBao self-hosted behind `SecretIdentityBackend`.
2. HashiCorp Vault or HCP Vault behind the same adapter.
3. AWS Secrets Manager.
4. GCP Secret Manager.
5. Infisical.
6. Doppler.
7. 1Password Connect / Secrets Automation.
8. Bitwarden Secrets Manager.
9. Continue host-local secret files with stricter conventions.

### Provider Comparison

| Provider | Fit | Decision |
| --- | --- | --- |
| OpenBao | Self-hosted, open-source Vault fork under open governance. Provides the Vault-compatible secret, auth, audit, lease, renewal, and revocation model CE needs. Current release state checked for this decision: OpenBao 2.5.x release notes, HTTP API, client-library compatibility, AppRole/JWT auth, and audit docs ([openbao-release-state], [openbao-http-api], [openbao-vault-compat], [openbao-approle], [openbao-jwt-oidc], [openbao-audit]). | Chosen default. |
| HashiCorp Vault / HCP Vault | Strong compatible profile, mature ecosystem, and possible managed/SLA path. Keeps the same conceptual API surface CE wants. | Supported compatible profile, not default because ce-ops#113 ratified OpenBao to avoid BUSL/procurement/cost dependency. |
| AWS Secrets Manager | Solid cloud leaf store for AWS-hosted static roots and rotation hooks. Does not by itself give CE a provider-neutral lease/revoke broker for all identities, GitHub Apps, and non-AWS seats. | Leaf/backend candidate, not CE's global broker default. |
| GCP Secret Manager | Solid cloud leaf store for GCP-hosted static roots and IAM-bound access. Similar limitation to AWS: useful below a broker, not the cross-fleet broker itself. | Leaf/backend candidate, not CE's global broker default. |
| Infisical | Good developer UX and machine-identity direction. ce-ops#113 research summary flagged dynamic secrets and audit retention as not in the desired low-cost/open default profile. | Runner-up for UX, not default for CE runtime brokering. |
| Doppler | Good static secret distribution and developer workflow product. Weaker fit for CE's lease/revoke/audit-before-issue broker requirement. | Bootstrap/static distribution only, not default. |
| 1Password Connect / Secrets Automation | Strong human/team vault UX and automation bridge. For CE, primarily static/bootstrap custody, not the default dynamic broker. | Bootstrap/static custody candidate, not default. |
| Bitwarden Secrets Manager | Useful low-cost static secret management. Does not satisfy CE's default dynamic lease/revoke/audit broker shape. | Bootstrap/static custody candidate, not default. |
| Host-local files | Requires no new service, but recreates the exact scatter, portability, audit, and shared-App custody problem ce-ops#113 is meant to retire. | Rejected as steady state. |

## Decision Outcome

Chosen option: **OpenBao self-hosted behind `SecretIdentityBackend`**.

The Operator has ratified OpenBao as the default backend ([ratification-addendum]).
CE will build a small value-free adapter surface first: frozen `SecretRef`,
`SecretRequest`, `SecretGrant`, and `IdentityDescriptor` records; backend
registry; fake backend; and a CI-pure OpenBao adapter with injected I/O. OpenBao
deployment, unseal, backup/restore, live migration, and secret import remain
blocked behind the B.1-B.5/B.6 gates recorded in the design document ([design]).

HashiCorp Vault/HCP remains a compatible managed profile because the adapter is
Vault-shaped and provider calls stay behind the seam.

## Consequences

- Good: CE gets a central secret plane direction with audit-before-issue and
  JIT minting.
- Good: ce-ops#117 can move shared GitHub App custody out of user hands once
  the later live deployment/migration gates are ratified.
- Good: per-dev identities can become portable across hosts and containers.
- Good: HashiCorp Vault/HCP remains viable through the same adapter.
- Bad: CE will operate a sensitive service; backup, unseal, audit, and upgrade
  runbooks become mandatory before Phase 3.
- Bad: AppRole bootstrap is itself a secret-zero problem; this ADR requires the
  response-wrapped/operator-injected model in the design, but does not deploy it.
- Bad: Signing roots and attestation keys are excluded from the first OpenBao
  runtime-token instance, which means CE must operate separate custody for those
  roots until a later ratified design.

## Non-Ratification Statement

This accepted ADR ratifies the backend/interface direction only. It does not
authorize a live OpenBao deployment, migration of live credentials, unseal or
backup custody, root-token handling, signing-root co-tenancy, or agent direct
access to OpenBao. B.6 secret migration is explicitly held.
