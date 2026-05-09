# Feature Specification: Creator Engine v0.1 Governance Substrate

**Feature Branch**: `001-v0-1-governance-substrate`
**Created**: 2026-05-08
**Status**: Draft
**Input**: User description: Creator Engine v0.1 Governance Substrate — prove that a tenant repository can describe agentic SDLC work through versioned specs and govern agent-authored mutations through explicit identity, authority, attestation, verification, and ratification rules. Source material: `/home/nefarious/projects/limitless/docs/superpowers/plans/2026-05-04-creator-engine-v0.1-plan.md`. Spec Kit is the first supported execution-spec substrate; Creator Engine wraps it with governance, identity, mutation-class, attestation, and ratification metadata.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tenant Identity & Authority Discoverable from Repo Artifacts (Priority: P1)

A tenant onboarding Creator Engine MUST be able to point at their repository
and answer, from repository artifacts alone, *which agent identity is allowed
to mutate which surfaces*. The identity contract names the tenant, the
source-host installation (e.g. a GitHub App), the agent actor identity, the
runtime/tool, the role, and the authority context for every agent that may
author governed work.

**Why this priority**: Without identity, every other governance principle
(author/approver separation, ratification, attestation) is unenforceable.
Identity is the join key the substrate is built on, and it is the first of the
five questions the v0.1 release commits to answering.

**Independent Test**: A reviewer with `git clone` and the substrate's
identity contract document can read a tenant identity record, list every
declared agent identity, and state — without consulting any external system —
which repositories and mutation classes each identity may touch. Verified by
constructing one example tenant identity record and walking the reviewer
through it cold.

**Acceptance Scenarios**:

1. **Given** a tenant repository with a Creator Engine identity record,
   **When** a reviewer reads the record, **Then** they can name the tenant,
   source host, agent app slug, agent actor identity, allowed repositories,
   and signing policy for that identity.
2. **Given** an attempt to record an agent identity missing one of the
   required fields, **When** the identity is loaded by the substrate's
   validator, **Then** the validator rejects it with a clear field-level
   error.
3. **Given** a mutation submitted by an actor not present in any identity
   record, **When** the mutation is reviewed, **Then** the substrate's
   contract states unambiguously that the mutation is not Creator-Engine-
   governed and MUST NOT be accepted as such.

---

### User Story 2 - Versioned Spec Format Defines Work and Acceptance (Priority: P1)

A tenant MUST be able to author a governed work item as a Markdown spec with
Creator Engine frontmatter that declares the spec's identity (id, title,
tenant, owner role, status), its mutation class and scope, its acceptance
criteria, its verification method, whether ratification is required, and a
reference to the identity policy that applies. This answers *which spec
format defines the work and acceptance criteria*.

**Why this priority**: Without a versioned spec format, "the spec" is
whatever an agent claims it is. The frontmatter contract turns prose
intentions into a machine-readable, lintable, ratifiable artifact and is the
second of the five questions the v0.1 release commits to answering.

**Independent Test**: A tenant can author a single Markdown file using the
v0.1 spec template, run the substrate's machine-checkable validator against
it, and have the validator confirm: required frontmatter fields are present,
the spec type is one of the declared taxonomy values, scope and acceptance
criteria are non-empty, verification is declared, and the spec is in a known
status. Verified by linting one well-formed and one deliberately malformed
example.

**Acceptance Scenarios**:

1. **Given** a Markdown file with complete Creator Engine frontmatter,
   **When** the spec validator runs, **Then** it reports the spec as valid
   and prints its declared id, type, mutation class, and ratification
   requirement.
2. **Given** a Markdown file missing `acceptance_criteria` or `verification`,
   **When** the Definition of Ready check runs, **Then** the spec is reported
   as not-ready-for-dispatch with the specific missing fields named.
3. **Given** an existing repository document (decision record, handoff,
   research report, retro), **When** the document is classified under the
   v0.1 spec taxonomy, **Then** it can be assigned a spec type without
   rewriting its body content.
4. **Given** the v0.1 spec frontmatter, **When** the document is opened in
   any plain Markdown reader, **Then** the body remains human-readable and
   the frontmatter does not break vanilla Spec Kit `spec.md` consumption.

---

### User Story 3 - Ratifier Identifiable per Mutation Class (Priority: P1)

A tenant MUST be able to look at the substrate's authority matrix and answer
*which human or role must ratify a completed mutation before merge* for any
declared mutation class, and the ratification flow MUST encode the
author/approver separation rule (the actor who authored a mutation cannot
also be the approving reviewer or ratifier).

**Why this priority**: Without an authoritative, repo-visible mapping from
mutation class to ratifier, "go ahead" in chat becomes merge authorization,
which is the failure mode the substrate is designed to eliminate. This is the
third of the five questions the v0.1 release commits to answering.

**Independent Test**: A reviewer reads the authority matrix and the
ratification flow document, picks any declared mutation class, and states
which role must ratify it, what evidence the ratifier requires, and which
roles are explicitly excluded from ratifying it (including the author).
Verified by walking through three distinct mutation classes with three
distinct ratifier outcomes.

**Acceptance Scenarios**:

1. **Given** the v0.1 authority matrix, **When** a reviewer selects any
   declared generic role category (`source`, `ratifier`, `reviewer`,
   `architect`, `implementer`, `verifier`, `observer`), **Then** they can
   list that role category's allowed instruction sources, allowed mutation
   classes, required ratifier, allowed communication surfaces, and required
   audit artifacts.
2. **Given** a mutation submitted by an agent whose role category is
   `implementer`, **When** ratification is sought, **Then** the matrix names a
   different role category as the required ratifier and the implementer is
   explicitly barred from self-ratifying.
3. **Given** a "go ahead" message in any communication channel, **When** a
   merge is attempted on its basis alone, **Then** the governance artifact
   states this is insufficient unless the matrix designates that channel and
   role as a valid ratification surface for that mutation class.
4. **Given** a mutation class touching identity, governance, security, or
   deploy, **When** ratification is sought, **Then** the matrix requires
   explicit human (not agent) ratification.

---

### User Story 4 - Verification Evidence and Attestation Record (Priority: P2)

A tenant MUST be able to answer, for any merged mutation, *which evidence
proves the mutation was verified* and *which attestation record ties the
mutation to identity, spec, mutation class, and ratifier*. The attestation
record MUST be reconstructable from repository artifacts alone in v0.1.

**Why this priority**: Verification and attestation together close the
governance loop. Without them, "done" remains a claim. These are the fourth
and fifth questions the v0.1 release commits to answering, and they share a
single artifact (the attestation record) that binds them.

**Independent Test**: A reviewer picks a merged mutation, locates its
attestation record in the repository, and reads off: the spec it fulfills,
the agent identity that authored it, its mutation class and the actions that
class permitted, the verification evidence (changed files, checks run,
review findings, approval state), and the ratifier identity. Verified end-to-
end by walking one example mutation through the substrate.

**Acceptance Scenarios**:

1. **Given** a merged mutation governed by Creator Engine, **When** an
   auditor reads its attestation record, **Then** the record contains a
   reference to the spec, the agent identity, the mutation class, the
   permitted-actions list, the verification evidence, and the ratifier.
2. **Given** an attempt to merge a governed mutation with no attestation
   record (or with required attestation fields missing), **When** the v0.1
   Definition of Done check runs, **Then** the mutation is reported as
   not-done and merge is blocked.
3. **Given** an attestation record, **When** read months later by an auditor
   with only `git clone`, **Then** every field resolves to repository content
   without needing an external system.
4. **Given** a mutation whose verification evidence is "the agent says it
   works", **When** evaluated against the Definition of Done, **Then** it is
   rejected as a self-claim with no verifiable artifact.

---

### User Story 5 - Redaction Gate Policy for Future Public or NDA-Visible Export (Priority: P2)

Before any tenant artifact (including LIMITLESS dogfood material) is eligible
for a future public reference or NDA-visible export workflow, the substrate
MUST define a negative policy gate: no such export may be approved unless a
redaction record exists that lists what was redacted, who approved the
redaction, and against which redaction policy. v0.1 defines the policy fields
and validation behavior only; it does not implement export workflows,
publishing flows, or corpus-export tooling.

**Why this priority**: Tenant data leaking into public reference material is
an irreversible failure for a governance substrate. Even though external
pilots and LIMITLESS-as-marketing are out of scope for v0.1, the substrate
must define and represent the gate now so that future export pathways
inherit it.

**Independent Test**: A reviewer evaluating a tenant artifact that declares a
future public or NDA-visible export intent can locate the redaction-gate
policy, identify the required redaction outputs, and confirm that the v0.1
validator rejects the declaration unless a redaction approval record is
referenced. Verified by validating one fixture that declares export intent
without redaction metadata and observing it reported as blocked. No actual
export workflow is executed in v0.1.

**Acceptance Scenarios**:

1. **Given** a tenant artifact containing tenant-specific identifiers,
   **When** that artifact declares future public or NDA-visible export intent,
   **Then** the redaction-gate policy requires a redaction record before any
   later export workflow may treat the artifact as eligible.
2. **Given** a redaction record, **When** read by an auditor, **Then** it
   identifies the source artifact, the redacted fields/regions, the approver,
   and the policy version applied.
3. **Given** the LIMITLESS dogfood corpus, **When** any artifact from it is
   marked as potentially public reference material, **Then** the gate marks
   publication as ineligible absent a redaction approval, regardless of
   artifact value.

---

### User Story 6 - LIMITLESS Dogfood Tenant Mapping (Priority: P3)

The substrate MUST ship a tenant fixture that maps the current LIMITLESS
fleet (identities, repositories, mutation classes, authority roles,
ratification flows) into the generic v0.1 contracts, demonstrating that the
substrate is project-agnostic and that the dogfood tenant has zero
unresolved identity fields.

**Why this priority**: Dogfooding proves the substrate works on a real
tenant and is the only way v0.1 acceptance can be claimed without external
pilots. The mapping doubles as a worked example for the next tenant. Lower
priority than P1/P2 because the contracts must exist before anything can be
mapped onto them, but still in v0.1 scope.

**Independent Test**: A reviewer reads the LIMITLESS dogfood mapping and
confirms that every required identity, spec, authority-matrix, and
attestation field has a non-`TBD` value, and that no LIMITLESS-specific
identifier (host names, channel names, bot slugs) appears in the substrate's
generic contract documents — only in the LIMITLESS fixture. Verified by
diffing the generic contracts against the LIMITLESS fixture and showing that
generic contracts contain no LIMITLESS strings.

**Acceptance Scenarios**:

1. **Given** the LIMITLESS dogfood mapping, **When** a reviewer walks the
   identity, mutation-class, authority, and ratification fields, **Then** no
   field is unresolved, deferred, or marked as `TBD`.
2. **Given** the substrate's generic contract documents (identity spec, spec
   schema, governance spec), **When** searched for LIMITLESS-specific
   identifiers, **Then** none are found; LIMITLESS-specific values appear
   only in fixture/example files.
3. **Given** the current `limitless-agent[bot]` behavior, **When** mapped
   onto the generic identity contract, **Then** every observed behavior
   resolves to a declared field in the contract with no field added solely
   for LIMITLESS.

---

### User Story 7 - Machine-Checkable Validation for the Substrate Contracts (Priority: P3)

A tenant MUST have at least one minimal, repo-runnable validator that checks
the substrate's contracts on tenant artifacts: spec frontmatter conformance,
identity-record completeness, mutation-class declaration presence, and the
Definition-of-Ready / Definition-of-Done field requirements. Validators MUST
be runnable from a fresh `git clone` without external services.

**Why this priority**: Machine-checkable validation turns the substrate from
"a set of documents reviewers should follow" into "a set of contracts a
reviewer can verify mechanically." Lower priority than the contract artifacts
themselves (P1/P2) because the contracts must exist before they can be
validated, but in scope for v0.1 because the user input lists "Minimal
machine-checkable validation/linting."

**Independent Test**: A reviewer with a fresh checkout runs the validator
against the bundled example tenant files (one well-formed, one deliberately
malformed) and observes: the well-formed example passes, and the malformed
example fails with a specific, contract-referenced error pointing at the
violated field. Verified end-to-end with no external service calls.

**Acceptance Scenarios**:

1. **Given** the substrate validator and a well-formed example tenant
   artifact, **When** the validator runs, **Then** it exits with a success
   status and reports the artifact as conformant.
2. **Given** the substrate validator and a malformed example (missing a
   required frontmatter field, or an undeclared mutation class), **When**
   the validator runs, **Then** it exits with a non-success status and
   reports which contract clause was violated.
3. **Given** a fresh `git clone` of the substrate repository with no
   network access, **When** the validator is invoked per the substrate's
   instructions, **Then** validation completes without external service
   dependencies.

---

### Edge Cases

- A repository document predating Creator Engine that lacks frontmatter
  entirely: the substrate MUST state how such documents are classified or
  grandfathered, without requiring rewrites of body content.
- Two governed specs declaring the same `id`: the substrate MUST treat this
  as a contract violation surfaced by the validator.
- An agent identity that is removed or rotated: the substrate MUST state how
  prior attestations referencing that identity remain auditable.
- A "go ahead" in a chat surface that the matrix does not designate as a
  ratification surface: the substrate MUST treat this as not a ratification.
- A mutation whose declared mutation class does not permit the actions taken
  (for example, a `docs` class mutation that modifies governance files):
  the substrate MUST surface this as a class/action mismatch.
- A redaction approval performed by the same actor who authored the
  underlying tenant artifact: author/approver separation MUST apply to
  redaction approvals as well.
- An attempt to bootstrap a tenant with no `human_ratifier_roles`: the
  substrate MUST treat this as an invalid identity record.
- A spec type not present in the v0.1 taxonomy: the substrate MUST reject
  the spec rather than silently accept an unknown type.

## Requirements *(mandatory)*

### Functional Requirements

**Identity & attestation contract**

- **FR-001**: The substrate MUST define a tenant identity record schema
  containing at minimum `tenant_id`, `source_host`, `agent_app_slug`,
  `agent_actor_id`, `runtime_tool`, `role_category`, `authority_context`,
  `human_ratifier_roles`, `mutation_classes`, `allowed_repositories`,
  `signing_policy`, and `attestation_storage_path`.
- **FR-002**: The identity contract MUST distinguish platform identity (who
  built the substrate) from tenant identity (who installs it).
- **FR-003**: The substrate MUST define a tenant source-host installation
  model that covers GitHub App installation as the v0.1 reference, while
  not hard-coding GitHub-specific assumptions into substrate-wide schemas.
- **FR-004**: The substrate MUST define an attestation record format that
  binds a mutation to its spec id, agent identity, mutation class,
  permitted-action list, verification evidence, and ratifier identity.
- **FR-005**: Attestation records MUST be reconstructable from repository
  artifacts alone in v0.1 (no external attestation store).

**Mutation-class taxonomy & author/approver separation**

- **FR-006**: The substrate MUST define a mutation-class taxonomy in which
  each class declares an action vocabulary, the actions an agent may take
  (for example: propose, edit, commit, open PR, attest, advise-only), and any
  reserved actions that require explicit human or ratifier authorization.
- **FR-007**: The substrate MUST encode the author/approver separation rule:
  the actor who authored a mutation MUST NOT be the approving reviewer or
  the ratifier of that same mutation, regardless of role.
- **FR-008**: The substrate MUST state that mutation classes touching
  merge, deploy, publish/export, credential or token issuance/revocation,
  organization, tenant, or repository settings, governance, security,
  identity, attestation-gate weakening, or redaction-gate weakening require
  explicit human (not agent) ratification. The taxonomy MUST NOT model
  `deploy`, `publish`, credential changes, organization/settings changes, or
  governance/redaction/attestation weakening as agent-permitted actions absent
  that ratification.

**Spec format**

- **FR-009**: The substrate MUST define a Creator Engine spec frontmatter
  schema containing at minimum `id`, `title`, `tenant`, `owner_role`,
  `status`, `mutation_class`, `scope`, `acceptance_criteria`,
  `verification`, `ratification_required`, and `identity_policy_ref`.
- **FR-010**: The spec format MUST be Markdown with frontmatter, not a new
  YAML or JSON DSL, and MUST remain readable by vanilla Spec Kit consumers.
- **FR-011**: The substrate MUST define a v0.1 spec type taxonomy including
  at least `decision_record`, `implementation_spec`, `research_report`,
  `handoff`, `retro`, `test_spec`, and `tenant_config`.
- **FR-012**: The substrate MUST allow existing decision records, handoffs,
  research reports, and retros to be classified under the taxonomy without
  rewriting their body content.
- **FR-012a**: The substrate MUST define additive Creator Engine wrapper
  metadata for Spec Kit `spec.md`, `plan.md`, and `tasks.md` artifacts without
  renaming or restructuring vanilla Spec Kit files. The wrapper metadata MUST
  include the fields needed to check mutation class, permitted action,
  verification evidence, and ratification status across spec, plan, task, and
  ratification time.
- **FR-012b**: The substrate MUST define plan-level and task-level metadata
  expectations, including at minimum a plan-level mutation-class summary,
  task-level mutation class/action/evidence declarations, and ratification or
  approval references sufficient to preserve author/approver separation.

**Definition of Ready / Definition of Done**

- **FR-013**: The substrate MUST define a Definition of Ready that blocks
  dispatch when scope, acceptance criteria, or verification fields are
  missing.
- **FR-014**: The substrate MUST define a Definition of Done that requires
  evidence (changed files, checks run, review findings, approval state) and
  rejects self-claims of completion.

**Governance authority matrix & ratification flow**

- **FR-015**: The substrate MUST publish an authority matrix that, for each
  generic role category (at minimum `source`, `ratifier`, `reviewer`,
  `architect`, `implementer`, `verifier`, `observer`), states allowed
  instruction sources, allowed mutation classes, required ratifier, allowed
  communication surfaces, and required audit artifacts. Tenant-specific role
  names such as LIMITLESS titles or team roles MUST appear only in tenant
  fixture mappings, not in the generic substrate schema.
- **FR-016**: The substrate MUST define a ratification flow that names the
  required ratifier role(s) per mutation class and states which surfaces
  count as valid ratification surfaces for each class.
- **FR-017**: Agent-authored review text MUST NOT count as ratification for
  merge, deploy, publish/export, credential or token issuance/revocation,
  organization, tenant, or repository settings, governance, security,
  identity, attestation-gate weakening, or redaction-gate weakening. For
  non-privileged classes, agent-authored review text MAY be recorded as
  review evidence only if the matrix authorizes that role instance for that
  evidence role; it MUST remain distinct from human ratification.
- **FR-018**: A "go ahead" or equivalent message in any communication
  surface MUST NOT count as merge authorization unless the governance
  artifact explicitly designates that surface and that role as a valid
  ratification surface for that mutation class.

**Redaction gate**

- **FR-019**: The substrate MUST define a redaction gate policy that makes a
  tenant artifact ineligible for any future public or NDA-visible reference
  workflow unless required redaction metadata and approval are present.
- **FR-020**: The substrate MUST define a redaction-record format that
  identifies the source artifact, the redacted fields/regions, the
  approving actor, and the redaction policy version applied.
- **FR-021**: Redaction approvals MUST be subject to author/approver
  separation: the redaction approver MUST NOT be the author of the
  underlying tenant artifact.

**LIMITLESS dogfood mapping**

- **FR-022**: The substrate MUST include a LIMITLESS dogfood mapping that
  maps the current LIMITLESS identities, repositories, mutation classes,
  authority roles, and ratification flow into the generic v0.1 contracts.
- **FR-023**: The dogfood mapping MUST contain zero unresolved identity
  fields and MUST live in fixture/example files separate from the generic
  contract documents.
- **FR-024**: The substrate's generic contract documents MUST contain no
  LIMITLESS-specific identifiers (host names, channel names, bot slugs);
  such identifiers MUST appear only in fixture files.
- **FR-024a**: The LIMITLESS fixture MUST include a canonical list of
  LIMITLESS-specific identifiers that generic contract validation searches
  for when enforcing FR-024 and SC-004. The list MUST be explicit enough to
  make the search reproducible and auditable, while avoiding secret values.

**Machine-checkable validation**

- **FR-025**: The substrate MUST ship at least one repo-runnable validator
  that checks: spec frontmatter conformance against the v0.1 schema,
  identity-record completeness, declared mutation class presence, and
  Definition-of-Ready / Definition-of-Done field presence.
- **FR-026**: The validator MUST run from a fresh `git clone` without
  requiring external service calls.
- **FR-027**: The validator MUST report violations with a contract-
  referenced error citing the specific field or rule violated.
- **FR-027a**: The validator MUST include the cross-artifact checks necessary
  to satisfy this feature's success criteria: duplicate spec-id detection,
  mutation class/action mismatch detection, required plan/task metadata
  presence, no LIMITLESS-specific strings in generic contract documents,
  attestation linkage for Definition of Done checks, and redaction gate
  metadata checks for artifacts declaring future public or NDA-visible export
  intent. v0.1 MUST NOT require live source-host API calls, deploy hooks,
  hosted policy enforcement, or runtime SaaS enforcement.

**Example tenant files**

- **FR-028**: The substrate MUST include at least one well-formed example
  tenant set (identity record, spec exemplar, attestation exemplar,
  redaction-record exemplar) that the validator accepts.
- **FR-029**: The substrate MUST include at least one deliberately
  malformed example for each major contract (identity, spec, attestation,
  redaction), used to demonstrate validator failure modes.

**Test / verification specification**

- **FR-030**: The substrate MUST publish a verification specification that
  describes how v0.1 completion itself is verified, including the checks an
  auditor runs to confirm each of the five governance questions can be
  answered from repo artifacts alone.
- **FR-031**: The verification specification MUST be reconstructable from
  the repo and MUST itself be a Creator-Engine-governed spec (eating the
  substrate's own dogfood at the meta level).

### Key Entities *(include if feature involves data)*

- **Tenant Identity Record**: a per-tenant declaration naming the tenant,
  the source-host installation, the agent app and actor, the runtime/tool,
  generic role category, authority context, human-ratifier roles, the declared
  mutation classes, the allowed repositories, the signing policy, and the
  attestation storage location. Joins agents to authority.
- **Mutation Class**: a named category of work item with a declared action
  vocabulary, a declared list of actions an agent may take under it (such as
  propose, edit, commit, open PR, attest, advise-only), and any actions
  reserved for explicit human or ratifier authorization (such as deploy).
  Joins work items to permitted actions.
- **Creator Engine Spec**: a Markdown document with v0.1 frontmatter that
  declares its id, title, tenant, owner role, status, mutation class,
  scope, acceptance criteria, verification method, ratification
  requirement, and identity-policy reference. The contract that an
  implementation fulfills.
- **Creator Engine Wrapper Metadata**: additive metadata for Spec Kit
  `spec.md`, `plan.md`, and `tasks.md` artifacts that preserves vanilla Spec
  Kit readability while making mutation class, permitted action,
  verification evidence, and ratification status checkable across the
  lifecycle.
- **Authority Matrix Entry**: one row of the governance matrix, naming a
  role and stating its allowed instruction sources, allowed mutation
  classes, required ratifier, allowed communication surfaces, and
  required audit artifacts.
- **Ratification Record**: the artifact that records who ratified a
  mutation, on which surface, against which spec and mutation class, with
  what evidence reviewed.
- **Attestation Record**: the durable artifact that binds a merged
  mutation to its spec id, agent identity, mutation class,
  permitted-action list, verification evidence, and ratifier identity.
  Reconstructable from the repo alone in v0.1.
- **Verification Evidence**: the concrete artifacts (changed files, checks
  run, review findings, approval state) that prove a mutation is done, as
  opposed to a self-claim of completion.
- **Redaction Gate Policy**: the named policy that governs whether a
  tenant artifact may be made public or NDA-visible, including required
  redaction outputs and approver constraints.
- **Redaction Record**: the artifact produced by the redaction gate,
  identifying the source artifact, redacted fields/regions, approver, and
  policy version.
- **LIMITLESS Dogfood Fixture**: the worked example that maps the current
  LIMITLESS fleet onto the generic v0.1 contracts. Lives in a fixture
  location separate from the substrate's generic contracts.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reviewer with `git clone` and the substrate documents,
  given any tenant artifact governed by Creator Engine, can answer all
  five v0.1 governance questions (identity, spec, ratifier, evidence,
  attestation) without consulting any external system.
- **SC-002**: A reviewer can determine in under fifteen minutes, using only
  repository artifacts, whether a given mutation is Creator-Engine-
  governed and whether it satisfies the v0.1 Definition of Done.
- **SC-003**: 100% of the named v0.1 deliverables (identity contract,
  source-host installation model, mutation-class taxonomy, spec
  frontmatter schema, Definition of Ready, Definition of Done, authority
  matrix, ratification flow, redaction gate, LIMITLESS dogfood mapping,
  validator, example tenant files, verification spec) exist as
  repository artifacts and pass the substrate's own validator.
- **SC-004**: 0 LIMITLESS-specific identifiers from the fixture's canonical
  non-secret identifier list appear in the substrate's generic contract
  documents, as confirmed by a reproducible exact-string search; all such
  identifiers live only in fixture/example files.
- **SC-005**: 0 fields in the LIMITLESS dogfood mapping are marked
  `TBD`, deferred, or unresolved.
- **SC-006**: For every well-formed example tenant artifact shipped, the
  validator reports success; for every deliberately malformed example, the
  validator reports a specific field-level or rule-level failure.
- **SC-007**: The validator completes a full pass on the bundled examples
  on a fresh `git clone` of the repository, on a developer workstation,
  with no external network requests, in under sixty seconds.
- **SC-008**: 0 governed mutations may merge under v0.1 rules without an
  attestation record that names spec, identity, mutation class,
  permitted actions, verification evidence, and ratifier; this is
  demonstrable by the substrate's own Definition of Done check.
- **SC-009**: 0 tenant artifacts that declare future public or NDA-visible
  export intent are treated as eligible under v0.1 rules without a redaction
  record that names source artifact, redacted regions, approver, and policy
  version; v0.1 does not execute export or publishing workflows.
- **SC-010**: An auditor unfamiliar with LIMITLESS can read the dogfood
  fixture and the generic contracts side by side and explain, in their
  own words, how a different tenant would replace LIMITLESS values
  without modifying the generic contracts.

## Assumptions

- v0.1 targets GitHub as the primary source-host installation reference;
  multi-SCM support beyond a compatibility note is out of scope per the
  source plan.
- Specs are authored as Markdown with frontmatter (per source plan §4.4);
  no new DSL is introduced.
- "Minimal machine-checkable validation/linting" means the smallest
  repo-runnable check set needed to answer the five v0.1 governance questions
  and satisfy this spec's success criteria: spec/frontmatter conformance,
  identity-record completeness, mutation-class declaration presence,
  Definition-of-Ready / Definition-of-Done field presence, duplicate spec-id
  detection, mutation class/action mismatch detection, required plan/task
  metadata presence, no LIMITLESS-specific strings in generic contracts,
  attestation linkage checks, and redaction gate metadata checks for artifacts
  declaring future public or NDA-visible export intent. It excludes live
  source-host enforcement, deploy hooks, hosted policy engines, SaaS runtime
  enforcement, and semantic redaction-content scanning.
- "Example tenant files" refers to project-agnostic templates; the
  LIMITLESS dogfood mapping is a separate, populated fixture, distinct from
  generic templates.
- Attestation records, ratification records, and redaction records all live
  inside the tenant repository at locations the tenant declares (e.g. via
  `attestation_storage_path` in the identity record); v0.1 does not
  introduce an external store.
- "Done" for v0.1 of this feature means the substrate exists, validates its
  own example files, and ratifier-approves its own planning bundle per the
  source plan §7 sequencing — not that any external pilot has consumed it.
- Spec Kit compatibility is preserved at the file level: vanilla Spec Kit
  `spec.md` / `plan.md` / `tasks.md` remain readable; Creator Engine adds
  metadata around them but does not rename or restructure them.
- The LIMITLESS dogfood corpus is NOT published as marketing or public
  reference material as part of v0.1 (per source plan §10).
- The substrate is itself governed by the Creator Engine constitution at
  `.specify/memory/constitution.md`; this spec, its plan, and its tasks
  are subject to that constitution's gates.
