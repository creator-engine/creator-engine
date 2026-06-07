# Creator Engine Governance

Creator Engine is a pre-1.0, ratification-governed substrate. This
document is the public on-ramp to its governance model. It is a
summary and an index; the authoritative documents live in the repo
and are linked below.

## Operating-model framing

Creator Engine is deterministic scaffolding over probabilistic
agentic engines. The substrate is closer to an operating-system
kernel and syscall boundary than to an ad hoc chatbot workflow: a
finite set of states, transitions, authorizing gates, evidence
artifacts, and ratifiers that probabilistic agents participate in
rather than bypass. The intent is to retain the learning and
reasoning of agentic engines while imposing predictability,
stability, reproducibility, traceability, and auditability for
enterprise-scale SDLC. In v0.1 the boundary is procedurally enforced
by human discipline plus the Feature 001 offline validator and CI
checks; a runtime gate/syscall executor is a possible future shape,
not a current capability.

The full doctrine — and the canonical prompt-file ratification phrase
used for future ratifier-scoped handoffs — is in
[`docs/architecture/agentic-sdlc-operating-model.md`](./docs/architecture/agentic-sdlc-operating-model.md)
under "Doctrine: deterministic syscall layer over probabilistic
agents" and §h. This GOVERNANCE.md remains the public on-ramp; the
operating-model document remains authoritative for SDLC mechanics.

## Version coexistence (v1 ↔ v3)

Creator Engine v1.0 and v3.x **coexist** on a shared governance base rather
than one replacing the other: v1.0 is retained as a working system and as the
substrate used to build v3.x. The two execution runtimes — the v1.0
coordination/launch runtime and the v3.x agent-native execution runtime — are
held import-disjoint so each stays independently-operable; the shared validator
engine grades both. This boundary is a governed invariant: it is declared in
`creator_engine_validator/_versions.py`, enforced by the `version_boundary`
check, and documented in
[`docs/architecture/VERSION_BOUNDARY.md`](./docs/architecture/VERSION_BOUNDARY.md).
Removing v1.0 machinery is **not** a routine change — cleanup is restricted to
code proven unused by both versions.

## Authority hierarchy

The source-of-truth hierarchy (Feature 002 FR-019) is:

1. [`.specify/memory/constitution.md`](./.specify/memory/constitution.md)
   — the constitution. Highest-authority document for any agent- or
   human-authored work in this repository.
2. Feature 001 governance substrate (ratified) — identity schema,
   mutation-class taxonomy, reserved-action vocabulary, authority
   matrix, attestation / ratification / redaction record formats, and
   the offline validator. See
   [`specs/001-v0-1-governance-substrate/`](./specs/001-v0-1-governance-substrate/)
   and the canonical contract documents under
   [`docs/contracts/`](./docs/contracts/).
3. Feature 002 canonical docs and operating model — the 25-state
   SDLC machine, Assignment Envelope contract, actor/tool ownership
   matrix, parallel-agent development model, and the conflict
   taxonomy. See
   [`specs/002-canonical-docs-and-operating-model/`](./specs/002-canonical-docs-and-operating-model/).
4. Tenant fixtures under [`tenants/`](./tenants/).
5. Working notes, session state, and handoffs (instance-local, not
   upstream-tracked).

Amendments to the constitution, the Feature 001 substrate, or the
Feature 002 operating model are themselves Creator-Engine-governed
mutations: a spec/plan/tasks triple, ratified by the Operator, versioned
per the constitution's Governance section.

## Roles

- **Operator.** The human governance authority for this repository
  (v1 machine value `source`; see
  [`docs/governance/V1_CANONICAL_TERMINOLOGY.md`](./docs/governance/V1_CANONICAL_TERMINOLOGY.md)
  §6 and
  [`docs/adr/ADR-0002-operator-terminology-reconciliation.md`](./docs/adr/ADR-0002-operator-terminology-reconciliation.md)).
  The Operator ratifies privileged mutations (see below), accepts or
  rejects amendments to the constitution and the canonical document
  set, and authorizes any operation that crosses a privileged-class
  boundary.
- **Maintainers.** Humans with commit/merge authority on the
  repository. Maintainers triage issues and pull requests, perform
  non-privileged merges that CI has verified, and escalate
  privileged-class changes to the Operator.
- **Contributors.** Anyone (human or agent) authoring a change.
  Contributors propose work through issues and pull requests
  consistent with [`CONTRIBUTING.md`](./CONTRIBUTING.md).
- **Agents.** Tool-using actors (for example, Claude Code) operating
  under explicit Assignment Envelopes. Agents are governed by the
  same authority and mutation-class rules as humans; agent actions
  are attributed and attestable.

## Mutation classes and ratification

Every governed mutation declares a mutation class. The baseline
taxonomy and reserved-action vocabulary are in
[`docs/governance/MUTATION_CLASS_MODEL.md`](./docs/governance/MUTATION_CLASS_MODEL.md).

The six **privileged classes** require Operator ratification:

- `deploy`
- `governance`
- `identity`
- `security`
- `attestation`
- `redaction`

The authority matrix — which class needs which ratifier, and how
SDLC transitions map to ratifiers — is in
[`docs/governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](./docs/governance/AUTHORITY_AND_RATIFICATION_MODEL.md).
Attestation record formats and bootstrap rules are in
[`docs/governance/ATTESTATION_MODEL.md`](./docs/governance/ATTESTATION_MODEL.md).

Author/approver separation (Feature 001 FR-007) and human ratification
(constitution Principle VI) apply at every privileged boundary:
single-actor approval of a privileged mutation is invalid.

## CI verifies; humans ratify

Creator Engine maintains a hard invariant: **CI verifies, it does not
ratify.** Automated checks confirm that artifacts are well-formed,
schemas validate, examples behave as declared, and policies are
followed; they do not by themselves authorize a privileged action.

- The required CI checks and the verifies-not-ratifies invariant are
  documented in
  [`docs/devops/CI_CD_STRATEGY.md`](./docs/devops/CI_CD_STRATEGY.md).
- The branch protection policy summary lives at
  [`.github/BRANCH_PROTECTION_POLICY.md`](./.github/BRANCH_PROTECTION_POLICY.md);
  branch protection rules themselves are configured on the platform
  and are a privileged operation.

## Privileged repo and platform operations

The following operations remain privileged regardless of who proposes
them, and must not be performed without explicit Operator/maintainer
authorization:

- Repository visibility changes (private ↔ public).
- Repository settings changes.
- Branch protection rule changes.
- Git history rewrites on shared branches.
- Deployments and environment promotions
  (see [`docs/devops/RELEASE_AND_DEPLOYMENT_STRATEGY.md`](./docs/devops/RELEASE_AND_DEPLOYMENT_STRATEGY.md)).
- Mutations to the constitution or to the canonical governance docs.
- Changes that broaden the redaction surface or weaken the
  no-LIMITLESS generic-path scan
  (see [`docs/security/SECURITY_MODEL.md`](./docs/security/SECURITY_MODEL.md)).
- Mutations to external trackers performed on behalf of the project.

Pull requests that attempt any of the above without prior
authorization will be closed pending the appropriate spec/plan/tasks
triple and Operator ratification.

## How to engage

- Read [`README.md`](./README.md) for orientation and the canonical
  document index.
- Read [`CONTRIBUTING.md`](./CONTRIBUTING.md) for the contributor
  workflow and local validation commands.
- Read [`SECURITY.md`](./SECURITY.md) before reporting anything that
  could be security-sensitive.
- Read [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md) before
  participating in project spaces.

## Related references

- [`.specify/memory/constitution.md`](./.specify/memory/constitution.md)
- [`docs/governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](./docs/governance/AUTHORITY_AND_RATIFICATION_MODEL.md)
- [`docs/governance/MUTATION_CLASS_MODEL.md`](./docs/governance/MUTATION_CLASS_MODEL.md)
- [`docs/governance/ATTESTATION_MODEL.md`](./docs/governance/ATTESTATION_MODEL.md)
- [`.github/BRANCH_PROTECTION_POLICY.md`](./.github/BRANCH_PROTECTION_POLICY.md)
- [`docs/devops/CI_CD_STRATEGY.md`](./docs/devops/CI_CD_STRATEGY.md)
- [`docs/devops/RELEASE_AND_DEPLOYMENT_STRATEGY.md`](./docs/devops/RELEASE_AND_DEPLOYMENT_STRATEGY.md)
- [`docs/security/SECURITY_MODEL.md`](./docs/security/SECURITY_MODEL.md)
