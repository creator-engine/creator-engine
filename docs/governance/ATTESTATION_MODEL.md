# Creator Engine Attestation Model

**Status**: Canonical. Authored under Sprint 0 Execution Slice A.

**Source-of-truth relationship**: SUMMARY. The authoritative attestation
record format is the Feature 001 contract — specifically FR-004,
FR-005, and FR-020a in
[`../../specs/001-v0-1-governance-substrate/spec.md`](../../specs/001-v0-1-governance-substrate/spec.md)
and the planned contract document at
`docs/contracts/attestation-record.md` (per the contract index at
[`../contracts/README.md`](../contracts/README.md)). This document
SUMMARIZES that contract and explains how attestations bind SDLC
transitions to evidence in the operating model. It MUST NOT introduce
a new attestation field; new fields require a Feature 001 amendment
and are flagged here per Feature 002 FR-021.

## a. Attestation record fields (Feature 001 FR-004)

The Feature 001 attestation record format binds a mutation to its
identity, spec, mutation class, evidence, and ratifier. Per FR-004 the
record contains at minimum:

- **Spec reference** — the `id` (and path) of the Creator Engine spec
  the mutation fulfills.
- **Agent identity** — the actor that authored the mutation, drawn
  from a tenant identity record per FR-001.
- **Mutation class** — drawn from the baseline taxonomy or a ratified
  tenant extension; see
  [`MUTATION_CLASS_MODEL.md`](./MUTATION_CLASS_MODEL.md).
- **Permitted-action list** — the actions the class permitted for this
  mutation, drawn from the reserved-action vocabulary per FR-006.
- **Verification evidence** — concrete artifacts proving the mutation
  is done: changed files, checks run (with results), review findings,
  approval state. Self-claims of completion ("the agent says it
  works") are rejected per FR-014 and constitution Principle VII.
- **Ratifier identity** — the actor who ratified the mutation, drawn
  from a tenant identity record. MUST be distinct from the author per
  FR-007.

Per FR-004, the record format MUST support a **pre-merge attestation
state** used to prove the mutation is mergeable and a **post-merge
finalization state** that adds the merge reference after merge.

## b. Pre-merge vs post-merge attestation states

The two attestation states map to specific SDLC transitions in the
Feature 002 operating model.

- **Pre-merge attestation (drafted at T15)**: created when local
  validation is complete and verification evidence has been recorded.
  The pre-merge record proves the mutation satisfies Definition of
  Done (FR-014) and that author/approver separation is intact. It
  carries every required field except the merge reference.
- **Post-merge finalization (recorded after T20/T24)**: after merge,
  the attestation is finalized with the merge reference (the merge
  commit SHA and target branch) and, for `deploy`-class mutations,
  the deploy evidence chain via T22–T24.

Both states are stored as YAML files, one record per file, per FR-020a
(see §c).

## c. Repository-native storage (Feature 001 FR-020a)

Attestation records, ratification records, and redaction records share
the same storage contract:

- **Format**: YAML, one record per file.
- **Location**: tenant-declared directory roots —
  `attestation_storage_path`, `ratification_storage_path`, and
  `redaction_storage_path` from the tenant identity record (FR-001).
- **Filename**: `<date>-<record-subject-id>.yml` within each declared
  root. For attestation and ratification records the subject id is the
  mutation id; for redaction records it is a redaction or artifact id
  declared in the record.
- **No append-only logs.** v0.1 does not permit Markdown-bodied
  records or append-only journal layouts.
- **Validator parses by configured directory glob + YAML parse only.**

This is the FR-005 guarantee in concrete terms: attestation records
are reconstructable from repository artifacts alone in v0.1, with no
external attestation store.

## d. Attestation linkage to SDLC transitions (T15, T22, T23, T24)

The Feature 002 SDLC Transition Matrix attaches attestation evidence
to four key transitions. The matrix itself is normative; this section
is a navigational summary.

- **T15 — Local Validation Complete → Attestation Drafted**. Hermes
  drafts the pre-merge attestation per FR-004. T15 is privileged
  (`attestation` class) and remains Phase 1; Source ratifies the
  attestation gate, never an agent.
- **T19/T20 — Scope Audit Complete → Ratification Complete → Merge
  Approved**. The ratification record (Feature 001 FR-016, FR-020a) is
  created and the merge authorization is recorded. The pre-merge
  attestation is the input the ratifier reads; the ratification record
  is the decision artifact.
- **T22 — Release Candidate Created → Deployment Approved**. Source
  ratifies the `deploy` mutation. The pre-merge attestation is
  extended with deploy-approval evidence per the future Feature 006
  deploy-attestation schema.
- **T23 — Deployment Approved → Deployment Complete**. The future
  release agent (Feature 006 deferred) records the deploy attestation
  per Feature 006's schema; the schema itself is deferred per Feature
  002 FR-025.
- **T24 — Deployment Complete → Post-release Evidence Recorded**. The
  post-release attestation finalizes the merge reference per FR-004
  and adds post-release evidence (rollback evidence, observability
  artifacts) per the Feature 006 schema.

Until Feature 006 ships, T23 and T24 are placeholders in the operating
model; Hermes audits attestation finalization on Source's behalf when
manual deploy events occur, but no deploy automation is authored in
v0.1.

## e. Ratification record vs attestation record (distinction)

Attestation records and ratification records share the FR-020a storage
contract but answer different questions.

- An **attestation record** answers: *what evidence proves this
  mutation is verified and binds it to identity, spec, class, and
  ratifier?* It is authored by the actor verifying the mutation
  (Hermes at T15) and finalized after merge.
- A **ratification record** answers: *who decided this mutation may
  proceed past a privileged gate, on what surface, against what
  spec/class, with what evidence reviewed?* It is authored by the
  ratifier (Source for privileged classes) and is consumed by Hermes
  to gate merge or by the future dispatcher/release agent to gate
  deploy.

The two records cross-reference each other by mutation id. Neither
substitutes for the other:

- A merged mutation MUST have a finalized attestation record. Without
  it, Definition of Done fails (FR-014).
- A privileged-class mutation MUST have a matching ratification
  record. Without it, FR-008 is unsatisfied and the validator surfaces
  the failure.

Agent-authored review text (Codex, future QA/security agents) is
attestation evidence input, never a ratification record (Feature 001
FR-017; Feature 002 FR-013).

## f. Bootstrap record grandfathering (constitution Principle VIII)

Per constitution Principle VIII, "until the attestation schema exists,
bootstrap batches MUST still record the available evidence in
repository-visible artifacts and commit history: changed files, checks
run, review findings, approval state, and ratifier identity. The first
attestation-schema feature MUST define how these bootstrap records are
normalized or grandfathered."

Operating-model implications:

- Pre-substrate bootstrap commits (the initial Spec Kit scaffold, the
  constitution ratification, Feature 001 itself, the Sprint 0
  Execution sequencing artifact, and the Sprint 0 Slice A canonical
  documentation batch) MUST remain auditable from git history alone;
  this is the v0.1 substitute for a formal attestation record until
  Feature 001's attestation contract is itself fully populated and
  ratified.
- Feature 001 contracts will define how these bootstrap records are
  normalized: either by retroactive `attestation_record.yml` entries
  (preferred, since they make the bootstrap auditable via the same
  validator surface as post-bootstrap work) or by explicit
  grandfathering rules naming the commits and the evidence anchors.
- Bootstrap records MUST NOT be used as precedent for bypassing
  post-bootstrap governance once attestation contracts are fully
  populated. The grandfathering is a one-time accommodation, not an
  ongoing exception.

This section flags a Feature 001 dependency per Feature 002 FR-021:
no new attestation field is introduced here; the precise
grandfathering rule for bootstrap commits is owned by Feature 001's
attestation contract document, which is enumerated in the contract
index at [`../contracts/README.md`](../contracts/README.md) as
`docs/contracts/attestation-record.md` and remains authoritative for
record-level details.

## Acceptance posture for this document

This ATTESTATION_MODEL.md satisfies Feature 002 Canonical Document
Specification #12: the attestation record field list matches Feature
001 FR-004; the storage layout matches FR-020a; the bootstrap
grandfathering policy is cited (constitution Principle VIII) and
flagged as a Feature 001 dependency per FR-021; no new attestation
field is introduced.
