# Creator Engine System Architecture Document (SAD)

**Status**: Canonical. Authored under Sprint 0 Execution Slice A.

**Source-of-truth relationship**: REFERENCE. The SAD defers to Feature
001 schemas, validators, and contracts under
[`../../specs/001-v0-1-governance-substrate/`](../../specs/001-v0-1-governance-substrate/)
and [`../contracts/`](../contracts/) for component shape; to
[`./agentic-sdlc-operating-model.md`](./agentic-sdlc-operating-model.md)
for SDLC mechanics; to
[`./agent-interaction-model.md`](./agent-interaction-model.md) for
actor surfaces and interaction patterns; to
[`./integration-map.md`](./integration-map.md) for boundaries with
external systems; and to
[`./parallel-agent-development-model.md`](./parallel-agent-development-model.md)
for parallel-pair runtime behavior. The SAD describes the static
architecture; the dynamic operating model lives in those neighbors.

## a. Component inventory

The substrate is a repo-native architecture: every component is a set
of files at known paths under the tenant repository (or under the
substrate repository, for substrate-development artifacts). Components
named by Feature 001 are listed here with their authoritative path,
purpose, and the FR(s) that constrain their shape.

| Component | Path | Purpose | Feature 001 FRs |
|---|---|---|---|
| Constitution | `.specify/memory/constitution.md` | Highest-authority governance document for agent-authored work. | Constitution §Authority & Boundaries; Feature 002 FR-019. |
| Spec substrate adapter (Spec Kit wrappers) | `*.creator-engine.yml` sidecars adjacent to `spec.md` / `plan.md` / `tasks.md` | Carry Creator Engine governance metadata (id, title, tenant, mutation class, scope, acceptance criteria, verification, ratification, identity policy refs) without modifying Spec Kit files. | FR-009, FR-010, FR-012, FR-012a, FR-012b. |
| Tenant identity registry | tenant-declared identity-record path under `tenants/<name>/` (or equivalent) | Names every governed agent identity, mutation classes, allowed repositories, signing policy, and the storage paths for attestation / ratification / redaction records. | FR-001, FR-002, FR-003. |
| Mutation-class taxonomy | `docs/contracts/mutation-class-taxonomy.yml` (baseline) + `schemas/mutation-class.schema.yaml` + `docs/contracts/mutation-class-taxonomy.md` | Declare the nine baseline classes, their action vocabulary, agent-permitted actions, and the `human_ratification_required` flag. | FR-006, FR-007, FR-008. |
| Authority matrix | `docs/contracts/authority-matrix.yml` (baseline) + `schemas/authority-matrix.schema.yaml` + `docs/contracts/authority-matrix.md` | Declare allowed instruction sources, mutation classes, ratifier roles, communication surfaces, and audit artifacts per role category. | FR-015, FR-016. |
| Definition of Ready | `docs/contracts/definition-of-ready.md` | Block `draft → ready` when scope, acceptance criteria, or verification fields are missing. | FR-013, FR-013a. |
| Ratification flow (contract document) | `docs/contracts/ratification-flow.md` (planned, sub-batch B per contracts/README.md) | Which surfaces count as valid ratification surfaces per mutation class; rules for "go ahead" messages. | FR-016, FR-017, FR-018. |
| Attestation record store | tenant-declared `attestation_storage_path` under `tenants/<name>/` or repo-local equivalent; one YAML file per record per FR-020a | Bind every governed mutation to spec, identity, mutation class, permitted actions, verification evidence, and ratifier; pre-merge and post-merge states. | FR-004, FR-005, FR-020a. |
| Ratification record store | tenant-declared `ratification_storage_path`; one YAML file per record per FR-020a | Record who ratified what mutation on which surface with what evidence reviewed. | FR-016, FR-020a. |
| Redaction record store | tenant-declared `redaction_storage_path`; one YAML file per record per FR-020a | Record source artifact, redacted regions, approver, and policy version. | FR-019, FR-020, FR-020a, FR-021. |
| Validator | `validators/` package (Python module `creator_engine_validator`); wheelhouses under `validators/wheelhouse/` and `validators/wheelhouse-dev/` | Repo-runnable offline validator for substrate contracts. | FR-025, FR-026, FR-027, FR-027a. |
| Example tenant files | `examples/` | Project-agnostic well-formed and deliberately malformed examples. | FR-028, FR-029. |
| Dogfood tenant fixture | `tenants/<tenant>/` | Worked example mapping a real tenant's fleet onto generic v0.1 contracts. | FR-022, FR-023, FR-024, FR-024a. |
| Verification specification | per Feature 001 verification spec contract (`verification-spec/` and `verification-spec.md` per `docs/contracts/README.md`) | Describe how v0.1 completion itself is verified. | FR-030, FR-031. |
| Operating-model canonical docs | this file plus the 16 sibling canonical docs enumerated in [`../../README.md`](../../README.md) | Express the SDLC operating model, agent interaction patterns, governance summary, quality and devops policy, and security model. | Feature 002 FR-022, FR-023; this Slice A batch. |

The repository layout under which these components live is summarized
in [`../../README.md`](../../README.md) §c.

## b. Data flow across the SDLC

The SDLC Transition Matrix in
[`./agentic-sdlc-operating-model.md`](./agentic-sdlc-operating-model.md)
§b is normative for ordering. The data flow at the architectural
level:

1. **Intent capture (T1–T2)**. Source records product intent; Hermes
   captures it into a working note. A PRD draft is authored on a
   feature branch by Claude Code.
2. **Governance ratification (T3, T5)**. Source ratifies the PRD and
   then the architecture; ratification records are committed under
   the ratification store.
3. **Spec authorship (T6–T9)**. Claude Code, inside a Hermes-prepared
   spec envelope, runs `/speckit-specify`, `/speckit-clarify`,
   `/speckit-plan`, and `/speckit-tasks`. The Spec Kit files
   (`spec.md`, `plan.md`, `tasks.md`) plus the Creator Engine
   sidecars are committed on the feature branch. Definition of Ready
   (FR-013) gates `draft → ready`.
4. **Batch approval and envelope authoring (T10–T12)**. Source
   approves the task batch; Hermes drafts an Assignment Envelope
   from the approved batch and provisions the worktree/branch.
5. **Implementation (T13–T14)**. Claude Code consumes the envelope
   inside the worktree, runs `/speckit-implement`, mutates only
   inside the envelope's `allowed_mutation_classes` and outside
   `prohibited_surfaces`, marks tasks `[X]` only after local
   validation, and reports evidence to Hermes.
6. **Verification and attestation (T15–T18)**. Hermes drafts the
   pre-merge attestation under the attestation store; Codex
   (Feature 004 deferred for identity) records review findings; CI
   (Feature 003 deferred for automation) records mechanical
   validation evidence; Hermes runs the scope audit.
7. **Ratification and merge (T19–T21)**. Source ratifies the mutation;
   the ratification record is committed; Hermes (or Source) executes
   merge mechanics; the merged feature branch lands on the canonical
   branch; a release-candidate tag is drafted.
8. **Deploy and post-release evidence (T22–T24, Feature 006
   deferred)**. Source ratifies the deploy at T22; the release agent
   (future) executes the deploy at T23 and records post-release
   evidence at T24; rollback evidence and observability artifacts are
   gathered under the Feature 006 policy.

Throughout, the only persistent state Creator Engine introduces is
the set of records under the attestation, ratification, and redaction
stores. v0.1 introduces no external state. Spec Kit files and Creator
Engine sidecars are themselves repository artifacts.

## c. Repository-native storage model (FR-005, FR-020a)

v0.1 ships repo-native storage only:

- **No external attestation store, ratification store, or redaction
  store.** Records live as YAML files inside the tenant repository.
- **One record per file.** No append-only logs and no Markdown-bodied
  records.
- **Tenant-declared directory roots.** The identity record's
  `attestation_storage_path`, `ratification_storage_path`, and
  `redaction_storage_path` fields name the root for each store.
- **Filename convention.** `<date>-<record-subject-id>.yml` within
  each root. For attestation/ratification records the subject is the
  mutation id; for redaction records it is a redaction or artifact
  id declared in the record.
- **Validator parses by directory glob + YAML parse only.**

Per Feature 001 FR-005, every attestation record MUST be
reconstructable from repository artifacts alone in v0.1: no external
attestation store exists. This is the v0.1 architectural commitment
that makes auditability from `git clone` alone non-negotiable.

## d. Integration boundaries

The full boundary map lives in
[`./integration-map.md`](./integration-map.md). Summary:

- **Spec Kit**: Creator Engine wraps Spec Kit with sidecars; vanilla
  Spec Kit files remain byte-identical.
- **GitHub**: PR/merge mechanics are GitHub's; branch protection, PR
  template, and `.github/` workflows are deferred to Feature 003.
  Branch-protection and CI policy changes are themselves privileged
  `governance`/`security`/`deploy` mutations.
- **CI**: mechanical validation only. CI verifies; CI never ratifies
  (FR-013). CI automation is deferred to Feature 003.
- **Work trackers** (Linear, Jira, etc.): out of scope for v0.1.
  Feature 002 specifies a tracker-agnostic work-item model; tracker
  integration is not implemented and not required.
- **Identity providers** (GitHub Apps, etc.): the v0.1 reference
  source-host installation model is GitHub App; FR-003 keeps the
  schema multi-SCM-compatible.

## e. Trust boundaries

Two trust boundaries are material:

1. **Author/approver boundary (Feature 001 FR-007)**. The author of a
   mutation MUST NOT be the approving reviewer or ratifier of that
   same mutation. This boundary cuts across every component:
   - Envelope: `created_by_actor_id` MUST be distinct from
     `consuming_actor_id` (FR-006 in Feature 002).
   - Spec: the actor recording `verified` is the author and MUST NOT
     be the ratifier (FR-013a).
   - Ratification: the ratifier MUST NOT equal any author named in
     the `tasks.creator-engine.yml` (the candidate v0.1 rule per the
     authority-matrix contract).
   - Redaction: the approver MUST NOT be the author of the
     underlying tenant artifact (FR-021).
2. **Substrate/tenant boundary (constitution Principle IX; FR-024)**.
   Generic-contract paths — `docs/contracts/`, `schemas/`,
   `validators/`, `templates/` — MUST contain no tenant-specific
   identifiers. Tenant-specific values live only under
   `tenants/<name>/`. This boundary preserves substrate portability.

Two further trust observations:

- **CI / agents do not ratify privileged classes.** CI is mechanical
  validation; agent-authored review text is review evidence, not
  ratification (FR-013, FR-017).
- **GitHub mechanics are not Creator Engine mutations.** Merges and
  tags are operations on the PR surface; the classified mutation is
  the change being merged, not the merge action itself.

## f. Extension points

The substrate is extended through documented contract surfaces rather
than by code patches:

- **Tenant fixtures** (`tenants/<tenant>/`): per-tenant identity records,
  mutation-class overlays, authority-matrix overlays, ratification-flow
  overlays, attestation/ratification/redaction storage roots,
  tenant-identifier leak scan corpus, and similar tenant-scoped data. A
  dogfood tenant fixture (its directory chosen by the tenant) supplies
  the worked example for Feature 001 acceptance.
- **Mutation-class extensions** (`tenants/<name>/mutation-classes.yml`):
  tenants MAY add classes beyond the nine baseline classes, drawing
  actions only from the reserved-action vocabulary. Baseline
  semantics MUST NOT be redefined.
- **Authority-matrix overlays** (`tenants/<name>/authority-matrix-overlay.yml`):
  alias baseline role categories to tenant-specific names, add
  surfaces, or add audit artifacts; cannot weaken privileged-class
  rules.
- **Ratification-flow overlays** (`tenants/<name>/ratification-flow.yml`):
  declare per-tenant ratification surfaces and policies on top of the
  substrate baseline.
- **Spec wrapper extensions**: additional fields in the
  `*.creator-engine.yml` sidecars are added only via Feature 001
  amendments; tenant-specific extension fields live in a tenant
  sub-section of the sidecar.

Phase 2 autonomy policies (low-risk auto-merge, autonomous batch-
pulling) are themselves extension points that require ratified
operating-model amendments (FR-028).

## g. Explicit dependencies on Feature 001 contracts

This SAD depends on the following Feature 001 contracts. Each is
referenced rather than restated:

- **Identity contract** (FR-001, FR-002, FR-003) — substrate's identity
  registry component.
- **Attestation record format** (FR-004, FR-005, FR-020a) — substrate's
  attestation store component.
- **Mutation-class taxonomy and reserved-action vocabulary** (FR-006,
  FR-007, FR-008) — see
  [`../governance/MUTATION_CLASS_MODEL.md`](../governance/MUTATION_CLASS_MODEL.md).
- **Spec wrapper schema** (FR-009, FR-010, FR-012a, FR-012b) — Spec
  substrate adapter component.
- **Definition of Ready** (FR-013, FR-013a) and **Definition of Done**
  (FR-014) — lifecycle gates.
- **Authority matrix** (FR-015, FR-016) and **ratification flow**
  (FR-016, FR-017, FR-018) — see
  [`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md).
- **Redaction gate policy and records** (FR-019, FR-020, FR-020a,
  FR-021) — see
  [`../security/SECURITY_MODEL.md`](../security/SECURITY_MODEL.md).
- **Validator** (FR-025, FR-026, FR-027, FR-027a) — repo-runnable
  offline validation component.
- **Dogfood tenant fixture** (FR-022, FR-023, FR-024, FR-024a) —
  tenant-fixture extension point.

Any architectural concept absent from Feature 001 that this SAD
requires is flagged as a Feature 001 dependency per Feature 002
FR-021 rather than redefined.

## h. Explicit deferrals to Features 003–006

Per Feature 002 FR-025, the following architectural surfaces are
deferred from v0.1 and named with their owning future feature. This
section also satisfies the SAD acceptance requirement to enumerate
deferrals.

| Architectural surface | Owning future feature | Why deferred |
|---|---|---|
| `.github/` workflows; baseline CI workflow; PR template; branch protection | Feature 003 (GitHub CI Governance) | CI policy changes are themselves privileged `governance`/`security`/`deploy` mutations; wiring CI is a separate ratified batch. |
| Codex reviewer identity record; QA agent identity record; security agent identity record; review/QA/security evidence schemas | Feature 004 (Independent Review / QA Agent Evidence) | Identity is privileged per FR-008; each governed identity requires its own ratified spec. |
| Hermes dispatcher; worktree lifecycle automation; sandboxing; safe parallel runtime | Feature 005 (Dispatch / Worktree / Sandbox Runtime) | Feature 002 specifies the manual protocol the runtime must obey; automation precedes the protocol only at the cost of freezing a wrong contract. |
| Release agent identity record; release records; deploy attestations; rollback evidence; GitHub environments; Source-approved deploy gates | Feature 006 (Release / Deployment Governance) | Deploy is privileged and Source-only per FR-008; deploy targets do not yet exist. |

Phase 2 autonomy expansion is OUT OF SCOPE for any of Features 002
through 006 absent a separately ratified amendment to the Phase 1 /
Phase 2 boundary (FR-028).

## Acceptance posture for this document

This SAD satisfies Feature 002 Canonical Document Specification #5:
every Feature 001 component named in §a (spec substrate adapter,
tenant identity registry, mutation-class taxonomy, authority matrix,
validator, attestation store, ratification store, redaction store,
verification spec) is enumerated; the storage-model section cites
FR-005 and FR-020a; any architecture concept absent from Feature 001
is flagged as a Feature 001 dependency per FR-021; deferrals to
Features 003–006 are explicit.
