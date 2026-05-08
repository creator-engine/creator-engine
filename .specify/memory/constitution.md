<!--
SYNC IMPACT REPORT
==================
Version change: (template, unratified) → 1.0.0
Bump rationale: Initial ratification of the Creator Engine constitution. All
template placeholders replaced with concrete principles, sections, and
governance rules. No prior ratified version existed.

Modified principles: N/A (initial ratification — no prior principles to rename)

Added sections:
  - Core Principles (I–XII): Spec-First Development; Repo-Native First (v0.1);
    Explicit Agent Identity; Mutation-Class Governance; Author/Approver
    Separation; Human Ratification; Verification Over Claims; Attestation
    Required; LIMITLESS as Dogfood, Not Dependency; Spec Kit Compatibility;
    YAGNI for v0.1; Security & Privacy as First-Class Constraints.
  - Definitions (minimal bootstrap vocabulary for Source, ratifier, approval,
    authority context, and governed mutation).
  - Bootstrap Applicability (initial constitution ratification and scaffolding
    are approved setup work; full schema/validator enforcement begins when
    the relevant v0.1 features define those contracts).
  - Authority & Boundaries (governance rules around Source approval, batch
    scope, prohibited unilateral agent actions).
  - Workflow & Verification Discipline (batch evidence requirements,
    repo-native auditability for v0.1).
  - Governance (amendment procedure, versioning policy, compliance review).

Removed sections: None.

Templates requiring updates:
  - ✅ .specify/templates/plan-template.md — Constitution Check section
    aligned to enumerate the twelve principles as plan gates.
  - ⚠ .specify/templates/spec-template.md — does NOT yet require identity /
    mutation-class metadata blocks. Deferred: Creator Engine wrapper schema
    is not yet specified in v0.1; spec.md may remain Spec-Kit-pure until the
    wrapper schema feature is itself spec'd. Revisit when the wrapper schema
    feature lands.
  - ✅ .specify/templates/tasks-template.md — task format now requires
    mutation class, permitted action, and verification evidence; every
    generated task list must include an attestation/evidence task even before
    the full attestation schema lands.
  - ✅ .specify/templates/checklist-template.md — generic; no changes needed.
  - ✅ AGENTS.md / CLAUDE.md — both currently point agents to "the current
    plan" for project context; no constitution-specific edits needed at
    this version.

Follow-up TODOs:
  - When the Creator Engine wrapper schema (identity + mutation-class +
    attestation + ratifier metadata over Spec Kit artifacts) is itself
    spec'd, update spec-template.md and tasks-template.md to require the
    exact machine-checkable wrapper fields.
-->

# Creator Engine Constitution

Creator Engine is a repo-native agentic SDLC governance substrate. Its purpose
is to make agent-authored software work auditable, spec-driven, identity-aware,
mutation-class governed, verified by evidence, and ratified by explicit
authority rules.

## Core Principles

### I. Spec-First Development

Product and substrate implementation MAY NOT begin without an approved spec,
plan, and task breakdown. Code that lacks a corresponding approved
spec/plan/tasks triple is out of scope and MUST NOT be merged. Spec, plan,
and tasks are the contract; implementation is the fulfillment of that
contract.

Bootstrap governance setup is the sole exception: repository creation,
Spec Kit scaffolding, and initial constitution ratification MAY occur as
explicitly approved setup work before the first feature spec exists. This
exception does not authorize product implementation, validator implementation,
schema implementation, or broad repository mutation without a later
spec/plan/tasks triple.

**Rationale**: Agent-authored work is only auditable if intent is fixed before
execution. Without a spec, "done" is undefined and reviewers have nothing to
check the work against.

### II. Repo-Native First (v0.1)

v0.1 MUST produce only files, schemas, examples, and validators inside a git
repository. v0.1 MUST NOT introduce a hosted SaaS control plane, external
policy daemon, or non-repo state store. Every artifact MUST be reconstructable
from `git clone` alone.

**Rationale**: Repo-native v0.1 keeps the substrate auditable from git history
and repository artifacts alone, avoids vendor lock-in, and allows tenants to
adopt Creator Engine without standing up infrastructure.

### III. Explicit Agent Identity

Agent-authored work MUST identify the tenant, source host, actor identity,
runtime/tool, role, and authority context. Work that cannot be attributed to a
concrete identity record MUST NOT be accepted as a Creator-Engine-governed
mutation.

**Rationale**: Without explicit identity, attestation, governance, and
author/approver separation are unenforceable. Identity is the join key that
makes every other principle checkable.

### IV. Mutation-Class Governance

Every executable work item MUST declare its mutation class and the actions
permitted for that class. Mutations MUST NOT exceed the actions their declared
class permits. Class declarations are part of the spec contract and are
checked at plan, task, and ratification time.

**Rationale**: Different kinds of changes (docs, code, schema, deploy,
governance, identity, security) carry different blast radii. Encoding class up
front lets reviewers and ratifiers apply proportionate scrutiny instead of
treating every mutation identically.

### V. Author/Approver Separation

The agent or human who authored a mutation MUST NOT be the approving reviewer
or the ratifier of that same mutation. Self-approval is invalid regardless of
role, seniority, or automation level.

**Rationale**: Single-actor approval collapses governance into trust. A second
party is required to make audit findings meaningful.

### VI. Human Ratification

Agents MAY propose, edit, test, and attest according to policy. Merge, deploy,
governance changes, security changes, and identity changes MUST require
explicit human or role-based ratification. Agents MUST NOT ratify their own or
other agents' work for these mutation classes.

**Rationale**: Agents are productive proposers but unsuitable as the final
authority on irreversible or trust-bearing mutations. Human ratification keeps
accountability anchored to a real person or named role.

### VII. Verification Over Claims

"Done" MUST mean evidence exists, not that an agent says it is done. A task is
not complete until verifiable artifacts (changed files, test results, review
findings, approval state) demonstrate completion. Self-reported completion
without evidence MUST be treated as in-progress.

**Rationale**: Agents are fluent enough to produce convincing completion
narratives that are not actually true. Evidence-based verification is the only
durable defense against confabulated progress.

### VIII. Attestation Required

Agent-authored mutations MUST produce a durable attestation record tying the
work to its spec, identity, mutation class, verification evidence, and
ratifier. Attestations MUST be reconstructable from repository artifacts in
v0.1. Mutations without a valid attestation record MUST NOT be accepted as
governed work once the v0.1 attestation schema and validator are defined.

Until the attestation schema exists, bootstrap batches MUST still record the
available evidence in repository-visible artifacts and commit history: changed
files, checks run, review findings, approval state, and ratifier identity.
The first attestation-schema feature MUST define how these bootstrap records
are normalized or grandfathered.

**Rationale**: Attestation is the auditable trail that links principles I–VII
together. Without it, the governance substrate cannot prove its own claims
weeks or months after the fact.

### IX. LIMITLESS as Dogfood, Not Dependency

LIMITLESS MAY be used as the first tenant fixture for examples, validators,
and end-to-end tests. Creator Engine artifacts MUST remain project-agnostic:
no LIMITLESS-specific assumption may be hard-coded into schemas, validators,
templates, or core logic. Tenant-specific data belongs in fixtures, not in
the substrate.

**Rationale**: Dogfooding accelerates v0.1 by giving us a real tenant to test
against, but Creator Engine's value depends on portability across tenants.
Conflating substrate and tenant erodes that.

### X. Spec Kit Compatibility

Spec Kit is the first supported feature-spec substrate. Creator Engine wraps
Spec Kit artifacts (spec.md, plan.md, tasks.md, constitution.md) with
identity, governance, attestation, and ratification metadata. Creator Engine
MUST NOT break Spec-Kit-only workflows; a spec authored against vanilla Spec
Kit MUST remain readable and usable.

**Rationale**: Replacing Spec Kit would force tenants to choose. Wrapping it
lets tenants adopt Creator Engine incrementally, on top of an existing spec
substrate they already understand.

### XI. YAGNI for v0.1

v0.1 MUST NOT build coordination protocols, drift detection, dashboards,
hosted policy engines, or multi-tenant SaaS behavior. Features beyond the
v0.1 charter (files, schemas, examples, validators, repo-native artifacts)
require explicit Source approval before they may be specced.

**Rationale**: Scope creep is the most common failure mode for governance
projects. v0.1 must ship a small, defensible substrate; ambition belongs in
later versions backed by real adoption signal.

### XII. Security & Privacy as First-Class Constraints

Security and privacy are design constraints, not afterthoughts. v0.1 does not
implement public-export or NDA-visible-corpus workflows. If a later spec
introduces such a pathway, redaction gates MUST be defined and enforced before
that pathway is used. New mutation classes that touch credentials, secrets,
identity, or external publication MUST declare their security and privacy
posture in the spec, and MUST be reviewed against that declaration at
ratification time.

**Rationale**: A governance substrate that leaks tenant data or weakens its
own redaction gates is worse than no substrate at all — it manufactures false
confidence. Security treated as a late polish step is security that fails.

## Definitions

For v0.1 bootstrap purposes:

- **Source**: the project owner/operator who has authority to approve Creator
  Engine governance direction and ratify privileged mutations until a more
  formal authority registry exists.
- **Ratifier**: a human or named role authorized by Source to accept a
  mutation after reviewing its evidence. The ratifier MUST be distinct from
  the author for the same mutation.
- **Approval**: an explicit recorded decision by Source or an authorized
  ratifier that a spec, plan, task set, amendment, or mutation may proceed.
  For v0.1 bootstrap work, approval may be recorded in git commits and
  repository artifacts until the attestation schema defines a stricter record.
- **Authority context**: the repository-visible facts that explain why an
  actor may perform or ratify a change: tenant, repository, actor identity,
  tool/runtime, role, approved batch, and scope.
- **Governed mutation**: any repository change that claims Creator Engine
  governance or changes Creator Engine-controlled artifacts, policies,
  schemas, validators, examples, or attestations.

These definitions are intentionally minimal. Feature 001 MUST replace or
extend them with machine-checkable schemas and validation rules.

## Bootstrap Applicability

This constitution governs all post-ratification Creator Engine work. The
initial repository creation, Spec Kit scaffold, and constitution ratification
are bootstrap governance setup performed under explicit Source approval.

During bootstrap, requirements that depend on not-yet-defined Creator Engine
schemas or validators are interpreted as design obligations, not immediate
machine-checkable gates. The first v0.1 feature MUST define the identity,
mutation-class, ratification, and attestation contracts needed to make those
obligations enforceable.

After those contracts land, new governed mutations MUST satisfy them. Bootstrap
records MUST remain auditable from git history and repository artifacts and
MUST NOT be used as precedent for bypassing post-bootstrap governance.

## Authority & Boundaries

This constitution supersedes conflicting agent suggestions, generated plans,
specs, and implementation tasks. When an agent-authored artifact conflicts
with this document, the constitution wins and the artifact MUST be revised.

Changes to identity, governance, ratification, attestation, security, or
public-export rules require explicit Source approval. Source approval MUST be
recorded in the amendment commit or in a repository artifact referenced by the
commit, and reflected in the version bump per the Governance section below.

Agents MAY draft and modify artifacts only within approved batch scope. A
batch is the unit of agent-authored work bounded by an approved spec, plan,
and tasks triple. Agents MUST NOT broaden batch scope unilaterally; scope
expansion requires a new approval.

Agents MUST NOT, without explicit human approval:

- merge code, configuration, or governance changes;
- deploy or publish artifacts to any environment or registry;
- rotate, issue, or revoke credentials or tokens;
- alter organization, tenant, or repository settings;
- weaken governance rules, attestation requirements, or redaction gates.

These actions are reserved for ratifiers regardless of how compelling the
agent's justification appears.

## Workflow & Verification Discipline

Every implementation batch MUST end with verifiable evidence: the set of
changed files, the tests or checks that were run (with results), the review
findings, and the approval state. Evidence MUST be captured in repository
artifacts — not in conversation transcripts, not in chat logs, not in
agent-only memory.

For v0.1, the substrate MUST remain auditable from git history and repository
artifacts alone. An auditor with `git log`, `git show`, and the repo contents
MUST be able to reconstruct: who proposed what, against which spec, with which
mutation class, with which evidence, and who ratified it. Any workflow choice
that breaks this property is out of scope for v0.1 regardless of convenience.

Spec, plan, and tasks artifacts MUST be kept in sync with implementation. If
implementation diverges from the approved triple, either the implementation is
revised back into compliance, or a new spec/plan/tasks revision is approved
before the divergence is accepted.

## Governance

This constitution is the highest-authority document in the repository for
agent-authored work. All PRs, reviews, and ratifications MUST verify compliance
with the principles above before approval.

**Amendment procedure**: Amendments MUST be proposed via a spec/plan/tasks
triple under the same governance rules as any other mutation. Amendments to
identity, governance, ratification, attestation, security, or public-export
rules additionally require explicit Source approval recorded in the amendment
commit. The Sync Impact Report at the top of this file MUST be updated on
every amendment.

**Versioning policy** (semantic versioning of this document):

- **MAJOR**: Backward-incompatible removal or redefinition of a principle, or
  a change that invalidates existing attestations, governance flows, or
  ratifier authority models.
- **MINOR**: New principle or section added, or a materially expanded rule
  that imposes new obligations.
- **PATCH**: Clarifications, wording fixes, typo corrections, or non-semantic
  refinements that do not change obligations.

**Compliance review**: Reviewers and ratifiers MUST treat this constitution as
the gating reference. Violations identified during review block ratification
until either resolved in the artifact under review or addressed via an
explicit, Source-approved amendment.

**Version**: 1.0.0 | **Ratified**: 2026-05-08 | **Last Amended**: 2026-05-08
