# Creator Engine Release and Deployment Strategy

**Status**: Canonical. Authored under Sprint 0 Execution Slice A.

**Source-of-truth relationship**: REFERENCE. Feature 006 ratifies
release/deploy automation, identity records, and evidence schemas;
this document specifies the policy release/deploy must obey. Feature
001 Principle XII (security and privacy as first-class constraints)
and FR-008 (privileged classes require human ratification) anchor the
ratification-class rules; no actual deploy automation is authored in
v0.1.

## a. Environment taxonomy

v0.1 recognizes three environments. The taxonomy is intentionally
small until deploy targets exist.

| Environment | Purpose | Promotion gate | Phase |
|---|---|---|---|
| `local` | Developer workstation / tenant workstation. Used to run validator, tests, and rehearsal of governed flows from a fresh `git clone`. | None. Anything runnable locally is runnable here. | Phase 1 today. |
| `staging` | Future tenant-owned staging environment for pre-production rehearsal. Not instantiated in v0.1. | Source ratification of the `deploy` mutation class for staging deploys (FR-008). | Phase 1 today; Phase 2-eligible target under a future ratified deploy policy. |
| `production` | Future tenant-owned production environment. Not instantiated in v0.1. | Source ratification of the `deploy` mutation class for production deploys (FR-008). Hermes audits attestation finalization on Source's behalf until Feature 006 instantiates the release agent. | Phase 1 today; remains Phase 1 (privileged). |

Until Feature 006 lands, no staging or production environment is
instantiated by Creator Engine itself. Tenants MAY have their own
environments; the deploy ratification rule in §b applies regardless.

## b. Deploy mutation-class ratification rule (Feature 001 FR-008)

The `deploy` mutation class is **Source-only**.

- Every deploy MUST be authorized by a Source-ratified
  ratification record per Feature 001 FR-016 and FR-020a.
- No agent (Claude Code, Codex, future QA / security / release
  agents) ratifies the `deploy` class.
- CI never ratifies the `deploy` class. CI passing is not deploy
  authorization.
- "Go ahead" messages on non-designated surfaces do not authorize
  deploy per Feature 001 FR-018.

The deploy ratification record names the build/release reference
(typically a release-candidate tag), the target environment, the
ratifier (Source), the evidence reviewed, and any deploy-specific
gates the policy requires. The record format follows the FR-020a
storage contract.

The deploy ratification is recorded at SDLC transition T22 (Release
Candidate Created → Deployment Approved). T23 (Deployment Approved →
Deployment Complete) and T24 (Deployment Complete → Post-release
Evidence Recorded) await Feature 006 instantiation: the future release
agent executes deploy steps only under Source-ratified deploy gates,
records deploy evidence, and never ratifies the `deploy` class.
Until then, Hermes may document intended gates and audit
Source-authorized evidence, but this Slice A policy does not claim
that v0.1 implements non-manual deploy completion.

Deploy automation, deploy targets, and the deploy-pipeline definition
itself are also privileged. Changes to deploy automation are
`deploy`/`governance`/`security`-class mutations per FR-008.

## c. Release-tag policy

Release candidates are tagged on the canonical branch.

- **RC tag format**: tenants choose the format (`v0.X.Y-rcN`,
  `release/<date>`, or equivalent). The format is recorded in the
  tenant's release-policy artifact.
- **RC creation (T21)**: Hermes creates the RC tag after merge
  approval (T20), drafts release notes, and attaches them to the
  RC. Until Feature 006 instantiates the release agent identity, RC
  creation is performed by Hermes under explicit Source
  authorization recorded in the merge authorization record.
- **RC content**: the RC tag MUST be reproducible from `git clone`
  alone (no external state). RC tags MUST NOT be re-pointed; a
  re-tag is a new RC with a new identifier.
- **Promotion**: an RC tag does NOT, by itself, authorize deploy.
  Deploy authorization requires the Source-ratified ratification
  record at T22 (§b).

The release-tag policy is itself a `governance`-class mutation;
changes to the policy require Source ratification.

## d. Rollback evidence requirement

Every deploy MUST be reversible by a recorded rollback path.

- **Rollback path identified before deploy**: at T22 (Deployment
  Approved), the ratification record names the rollback path
  (typically the prior RC or the prior production tag) and the
  conditions under which rollback is initiated.
- **Rollback execution evidence**: if rollback is initiated, the
  rollback execution produces a rollback evidence record under the
  Feature 006 schema (deferred). Until Feature 006 instantiates the
  schema, rollback evidence is captured in repository-visible
  artifacts per constitution Principle VIII: the rollback's git
  reference, the commands run, the captured logs, and a
  post-rollback attestation note linked to the original deploy
  attestation.
- **No silent rollbacks**: a rollback that does not produce evidence
  is itself a governance failure. The rollback path is part of the
  deploy ratification record; executing it without evidence violates
  Definition of Done (FR-014).

The rollback-evidence requirement applies to staging deploys as well
as production deploys; the bar scales with environment risk but the
record-keeping does not lapse.

## e. Secrets policy summary

Secrets and credentials are governed by Feature 001's `security`
class and by constitution Principle XII. The summary here defers to
the full
[`../security/SECURITY_MODEL.md`](../security/SECURITY_MODEL.md):

- Credentials and tokens are themselves `security`-class artifacts.
  Issuance and revocation are reserved-restricted actions in the
  reserved-action vocabulary (`issue_credential`,
  `revoke_credential` — see
  [`../governance/MUTATION_CLASS_MODEL.md`](../governance/MUTATION_CLASS_MODEL.md)
  §b).
- Source-only ratification applies to any credential mutation per
  FR-008. No agent issues or revokes credentials in v0.1.
- Credentials and tokens MUST NOT live in repository artifacts
  beyond opaque references (env var names, secret-store ids).
- Deploy targets that need credentials MUST source them from a
  tenant-owned secret store at deploy time; Creator Engine itself
  stores no live secrets.

## f. Observability requirement summary

v0.1 ships no deploy automation, so observability is specified only
as policy that future deploy automation must obey.

- **Required observability artifacts (post-Feature-006)**: deploy
  start/end timestamps, build/release reference, target environment,
  health-check outcome, basic latency/error indicators where
  applicable, and the deploy attestation reference.
- **No external SaaS dashboards in v0.1**: observability artifacts
  live as repository records (Feature 006 schema deferred) so that
  audit trail remains reconstructable from `git clone`.
- **Constitution Principle II remains floor**: observability surfaces
  cannot become a hosted control plane; they remain repo-native
  records of deploy events. Tenants MAY add their own dashboards;
  Creator Engine governance does not require a dashboard.

The full observability schema and storage contract land with Feature
006.

## g. Incident-response expectation summary

Incident response is the operational counterpart of the rollback
requirement (§d).

- **Detection**: deploy failures, health-check regressions, or
  rollback-evidence anomalies trigger incident response.
- **Author/approver separation persists**: the actor who declares an
  incident MUST NOT be the actor who authorized the deploy that
  caused it (FR-007). Source remains the ratifier for any mitigation
  that changes governance, identity, or security posture.
- **Records**: incident response produces repository-visible
  artifacts: the incident summary, the mitigation chosen, the
  rollback evidence (§d), and any post-incident attestation
  amendments per FR-004.
- **Quarantine of deploy capability**: if an incident reveals a
  systemic deploy capability bug, deploy capability MAY be
  quarantined (further deploys halted) under Source ratification
  pending fix. The quarantine is itself a `governance`-class
  mutation.
- **Out-of-scope for v0.1**: paging, on-call rotations, and
  external incident-management integrations remain tenant-owned;
  Creator Engine specifies the evidence shape, not the workflow.

## h. Feature 006 deferral

The following surfaces are deferred to Feature 006 (Release /
Deployment Governance):

- Release agent identity record per Feature 001 identity contract.
- Release records and their schema.
- Deploy attestation records and their schema.
- Rollback evidence records and their schema.
- Post-release attestation finalization records and their schema.
- GitHub environments and environment gates.
- Source-approved deploy gates as a structured contract.
- Deploy automation (CI/CD pipelines that actually execute deploys).

The `deploy` mutation class remains Source-only per FR-008 regardless
of Feature 006 automation. Feature 006 implements the execution
surface; ratification belongs to Source.

No deploy automation is authored in Slice A of Sprint 0 Execution.
The Sprint 0 exit gate "Release/merge/deploy governance is
documented, even where deploy automation remains deferred" is the
gate this document advances.

## Acceptance posture for this document

This RELEASE_AND_DEPLOYMENT_STRATEGY.md satisfies Feature 002
Canonical Document Specification #16: deploy-as-privileged-class is
explicit (Source-only per FR-008); the Feature 006 deferral is
explicit; the environment gates table is populated; no actual deploy
automation is authored.
