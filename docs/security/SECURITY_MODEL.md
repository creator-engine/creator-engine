# Creator Engine Security Model

**Status**: Canonical. Authored under Sprint 0 Execution Slice A.

**Source-of-truth relationship**: SUMMARY. Feature 001 security and
redaction contracts are authoritative for record shape and validator
behavior; constitution Principle XII is authoritative for treating
security and privacy as design constraints. This document
SUMMARIZES and LINKS; it does not redefine.

## a. Security as design constraint (constitution Principle XII)

Security and privacy are design constraints, not afterthoughts.

- v0.1 does NOT implement public-export or NDA-visible-corpus
  workflows. If a later spec introduces such a pathway, redaction
  gates MUST be defined and enforced before that pathway is used.
- New mutation classes that touch credentials, secrets, identity, or
  external publication MUST declare their security and privacy
  posture in the spec and MUST be reviewed against that declaration
  at ratification time.
- A governance substrate that leaks tenant data or weakens its own
  redaction gates is worse than no substrate at all — it
  manufactures false confidence. Security treated as a late polish
  step is security that fails.

Operating-model implications:

- Every governed mutation has a mutation class declaration (Feature
  001 FR-006); security-sensitive work cannot be ungoverned.
- Privileged classes that touch security or identity require Source
  ratification per Feature 001 FR-008 (see §b).
- Author/approver separation (Feature 001 FR-007) applies to
  redaction approvals (Feature 001 FR-021) and to every other
  security-sensitive mutation; single-actor approval is invalid.
- Constitution Principle V (Author/Approver Separation) and
  Principle VI (Human Ratification) supply the broader rules these
  security mechanics implement.

## b. Security mutation class definition and Source-only ratification

The `security` mutation class is one of the six privileged classes
enumerated in Feature 001 FR-008:

- `deploy`
- `governance`
- `identity`
- **`security`**
- `attestation`
- `redaction`

Privileged classes MUST set `human_ratification_required: true` per
Feature 001 FR-006/FR-008 and the contract at
[`../contracts/mutation-class-taxonomy.md`](../contracts/mutation-class-taxonomy.md)
§FR-008.

For the `security` class specifically:

- **Ratifier**: Source-only. Per the Feature 001 authority matrix
  contract, every authority-matrix row whose
  `allowed_mutation_classes` contains `security` MUST resolve
  `required_ratifier_role` to a human-eligible role (`source` or
  `ratifier`).
- **Agent permitted actions**: no reserved-restricted action (no
  `issue_credential`, `revoke_credential`, `alter_repo_settings`,
  `alter_tenant_settings`, `alter_org_settings`, etc.) per the
  Reading A strict rule.
- **No silent automation**: CI workflow files, branch protection,
  and `.github/` content that touch security posture are themselves
  `security` (and often `governance` and `deploy`) class mutations
  requiring Source ratification.

The future security agent (Feature 004 deferred) MUST NOT ratify
the `security` mutation class (Source-only). The security agent's
allowed mutation classes are `docs` only (security finding records,
vulnerability reports); never `code`, `schema`, or any privileged
class. The security agent's findings are review evidence, never
ratification (Feature 001 FR-017; Feature 002 FR-013).

## c. Redaction gate summary (Feature 001 FR-019, FR-020, FR-020a, FR-021)

The redaction gate is the negative policy that makes a tenant
artifact ineligible for any future public or NDA-visible reference
workflow unless redaction metadata and approval are present.

Summary of the Feature 001 redaction-gate contract (authoritative
detail lives at the planned `docs/contracts/redaction-gate-policy.md`
and `docs/contracts/redaction-record.md` per
[`../contracts/README.md`](../contracts/README.md)):

- **FR-019 — gate**: No tenant artifact may be treated as eligible
  for a future public or NDA-visible export workflow unless required
  redaction metadata and approval are present.
- **FR-020 — record format**: A redaction record identifies the
  source artifact, the redacted fields/regions, the approving actor,
  and the redaction policy version applied.
- **FR-020a — storage**: Redaction records are YAML files, one
  record per file, under `redaction_storage_path` declared in the
  tenant identity record, with filename
  `<date>-<record-subject-id>.yml` where the subject id is a
  redaction or artifact id declared in the record.
- **FR-021 — author/approver separation**: The redaction approver
  MUST NOT be the author of the underlying tenant artifact.

v0.1 does NOT execute export, publish, or external reference
workflows. The gate is enforced as a metadata precondition: any
artifact that declares future public or NDA-visible export intent
must reference a valid redaction record before any later export
workflow may treat it as eligible.

The `redaction` mutation class is itself one of the six privileged
classes (Feature 001 FR-008). Changes to the redaction gate policy,
the redaction record schema, or any tenant's redaction-policy overlay
require Source ratification. Agents MAY draft redaction records as
proposals; only Source (or a Source-authorized human ratifier
distinct from the artifact author) may approve a redaction.

## d. Secrets policy summary

Secrets and credentials are governed by the `security` mutation
class and by the reserved-action vocabulary's reserved-restricted
actions (see
[`../governance/MUTATION_CLASS_MODEL.md`](../governance/MUTATION_CLASS_MODEL.md)
§b).

- **No live secrets in the repository.** Credentials and tokens
  MUST NOT appear in repository artifacts beyond opaque references
  (env var names, secret-store ids, public key fingerprints).
- **Issuance and revocation are reserved-restricted.** The
  reserved-action vocabulary names `issue_credential` and
  `revoke_credential` as reserved-restricted actions; per Reading A
  strict, no baseline class's `agent_permitted_actions` may include
  them. Issuance and revocation are reserved for Source via the
  ratification flow.
- **Deploy-target secrets are tenant-owned.** Deploy targets that
  need credentials source them from a tenant-owned secret store at
  deploy time; Creator Engine itself stores no live secrets.
- **Bot tokens for governed agents**: tenant identity records
  reference signing policy per FR-001 but do not embed live
  credentials. Token rotation is a `security`/`identity` mutation
  per FR-008.

The full secrets contract is owned by Feature 001 (and any tenant
secret-store overlay). This document references rather than
restates.

## e. Credentials rotation policy summary

Credential rotation is a `security` and `identity` mutation per
Feature 001 FR-008.

- **Rotation cadence**: tenants set rotation cadences in their own
  identity / security policy artifacts. Creator Engine does not
  prescribe a global cadence; constitution Principle XII demands
  that rotation be specified somewhere, not that it follow a
  uniform schedule.
- **Rotation authorization**: every credential rotation MUST be
  authorized by a Source-ratified ratification record per FR-016 and
  FR-020a. The ratification record names the credential or token
  identifier (opaque, never the live secret), the rotation
  rationale, and the ratifier.
- **Post-rotation evidence**: rotation produces an evidence trail
  linked to the affected identity record; prior attestations
  referencing the rotated identity remain auditable per Feature 001
  Edge Case ("An agent identity that is removed or rotated").
- **Emergency rotation**: an emergency rotation (suspected secret
  compromise) is still a Source-ratified mutation; ratification
  MAY be retroactive only when Source's authorization is recorded in
  a repository artifact ahead of the rotation event, even if the
  formal record is committed shortly after.

## f. Security-finding-record schema reference (Feature 004 deferral)

The security-finding-record schema is deferred to Feature 004
(Independent Review / QA Agent Evidence). Per Feature 002 FR-021,
this document flags the dependency rather than inventing a competing
contract.

Until Feature 004 lands, security findings are captured in
repository-visible artifacts per constitution Principle VIII:

- Vulnerability reports authored as `docs`-class records (e.g.,
  Markdown files under a tenant-declared security findings root, or
  attached to a Creator-Engine-governed spec).
- Tenant-identifier leak scan outputs from `python -m
  creator_engine_validator scan-no-limitless` (current command name
  retained from Feature 001).
- Redaction-gate scan results.
- PR review comments recorded as review evidence; review evidence
  is NEVER ratification for the `security` class per FR-017.

Post-Feature-004, the security-finding record will be a YAML file
under the tenant's Feature 004-declared security-findings path
(analogous to the attestation / ratification / redaction record
stores at FR-020a) and will link to the SDLC transition the finding
affects (typically T16 or T17 as Feature 004 specifies).

## g. Escalation paths

Security incidents and security-policy conflicts follow the
operating-model escalation path summarized in
[`./../architecture/agent-interaction-model.md`](../architecture/agent-interaction-model.md)
§g.

- **Detected by**: validator output (e.g., tenant-identifier leak
  scan failures, redaction-gate failures), reviewer findings, CI
  evidence, or operator observation.
- **Classification**: every security-policy conflict is an
  `authority` conflict per Feature 002 FR-018 — that is, any
  attempt to mutate the security mutation class, redaction gate,
  identity record, or attestation gate absent ratification hard-
  stops work.
- **Resolver**: Source. Work HALTS pending Source ratification.
- **Required evidence**: the offending change is reverted unless
  Source ratifies it; a ratification record (or revert record) is
  committed before any downstream transition advances.
- **Post-incident**: the response produces repository-visible
  artifacts — the incident summary, the chosen mitigation, the
  rollback or revert evidence, and any post-incident attestation
  amendments per FR-004.

Constitution Principle V (Author/Approver Separation) and Principle
VI (Human Ratification) supply the broader rules these escalation
mechanics implement. A "go ahead" message on a non-designated
surface does NOT authorize any privileged security mutation per
FR-018.

## Acceptance posture for this document

This SECURITY_MODEL.md satisfies Feature 002 Canonical Document
Specification #17: Principle XII is cited; the `security` mutation
class is explicit as Source-only (Feature 001 FR-008); the redaction
gate summary is present (FR-019, FR-020, FR-020a, FR-021); the
secrets policy summary is present; the credentials rotation policy
summary is present; the security-finding-record schema deferral to
Feature 004 is explicit; escalation paths are linked.
