# Creator Engine v0.1-docs Product Requirements Catalog

**Status**: Canonical. Authored under Sprint 0 Execution Slice A.

**Source-of-truth relationship**: REFERENCE. This document defers to
Feature 001 functional requirements (FR-001 through FR-031) for
substrate semantics and to Feature 002 normative sections for
operating-model semantics. It catalogs load-bearing product
requirements with traceability; it does not redefine any FR.

## a. Requirement traceability summary

Each row in this catalog answers: "Which product problem motivates this
requirement, and where is the contract or operating-model rule that
makes it checkable?" Traceability is by Feature 001 FR id, Feature 002
FR id, or Feature 002 normative section anchor.

Five product problems anchor the v0.1 scope, taken from
[`PRD.md`](./PRD.md) §c:

- **P1 — auditability from `git clone` alone**: agent-authored work is
  not reviewable months later without a repo-native record.
- **P2 — author/approver separation**: trust-by-default collapses
  governance into a single actor.
- **P3 — bounded agent invocation**: an unbounded `/speckit-implement`
  bypasses the substrate exactly when the agent acts.
- **P4 — review vs ratification clarity**: CI passes and agent review
  text are too easily mistaken for ratification.
- **P5 — repo-native dogfooding without tenant lock-in**: the substrate
  must work on a real tenant while staying project-agnostic.

## b. Functional product requirements

### PR-F-001 — Tenant identity discoverable from repo artifacts

**Problem**: P1.

**Requirement**: A tenant's identity record MUST live as a YAML file
inside the tenant's repository and MUST name tenant, source-host
installation, agent app, agent actor, runtime/tool, role category,
authority context, human ratifier roles, mutation classes, allowed
repositories, signing policy, and attestation / ratification /
redaction storage paths.

**Traces to**: Feature 001 FR-001, FR-002, FR-003.

**Acceptance**: A reviewer can name every required field from the
identity record alone without consulting any external system.

### PR-F-002 — Spec body remains vanilla Spec Kit

**Problem**: P1, P5.

**Requirement**: Spec body content (`spec.md`, `plan.md`, `tasks.md`)
MUST remain byte-identical to vanilla Spec Kit; Creator Engine
governance metadata MUST live in adjacent YAML sidecars
(`spec.creator-engine.yml`, `plan.creator-engine.yml`,
`tasks.creator-engine.yml`).

**Traces to**: Feature 001 FR-009, FR-010, FR-012a, FR-012b;
constitution Principle X.

**Acceptance**: Opening any Spec Kit file in a vanilla Spec Kit reader
shows no Creator-Engine-specific content; governance fields resolve
from the sidecar.

### PR-F-003 — Mutation class declared per work item

**Problem**: P2, P3.

**Requirement**: Every executable Creator Engine work item MUST
declare its mutation class from the nine baseline classes (`docs`,
`code`, `schema`, `deploy`, `governance`, `identity`, `security`,
`attestation`, `redaction`) or from a tenant extension; declared
permitted actions MUST be drawn from the reserved-action vocabulary.

**Traces to**: Feature 001 FR-006; Feature 002 §SDLC Transition Matrix,
§Canonical Document Specifications #11.

**Acceptance**: Validator surfaces class/action mismatches per Feature
001 FR-006/FR-027a.

### PR-F-004 — Privileged classes require human ratification

**Problem**: P2, P4.

**Requirement**: The mutation classes `deploy`, `governance`,
`identity`, `security`, `attestation`, and `redaction` MUST require
explicit human ratification; agent-authored review text MUST NOT count
as ratification for these classes; "go ahead" on a non-designated
surface MUST NOT count as merge authorization.

**Traces to**: Feature 001 FR-008, FR-017, FR-018; Feature 002 FR-013.

**Acceptance**: For any privileged-class mutation, the ratification
record names a human ratifier per the authority matrix and the
ratification flow.

### PR-F-005 — Author/approver separation enforced

**Problem**: P2.

**Requirement**: The actor who authored a mutation MUST NOT be the
approving reviewer or the ratifier of that same mutation. Assignment
Envelope `created_by_actor_id` and `consuming_actor_id` MUST be
distinct.

**Traces to**: Feature 001 FR-007; Feature 002 FR-006.

**Acceptance**: A spec that names the same actor as author and
ratifier is rejected by the v0.1 contracts; an envelope whose author
equals its consumer is malformed per FR-006.

### PR-F-006 — Definition of Ready blocks unready dispatch

**Problem**: P1, P3.

**Requirement**: A spec MUST NOT advance from `draft` to `ready`
without non-empty `scope`, `acceptance_criteria`, and `verification`
fields; `in_progress` MUST NOT be dispatched on a not-ready spec.

**Traces to**: Feature 001 FR-013, FR-013a; contract
[`docs/contracts/definition-of-ready.md`](../contracts/definition-of-ready.md).

**Acceptance**: Validator's `definition_of_ready` check rejects
incomplete sidecars and cites the missing fields.

### PR-F-007 — Definition of Done requires evidence

**Problem**: P1, P4.

**Requirement**: A spec MUST NOT enter `done` without an attestation
record satisfying Feature 001 FR-004 and FR-008. Self-claims of
completion ("the agent says it works") MUST be rejected.

**Traces to**: Feature 001 FR-014, FR-013a; constitution Principle VII.

**Acceptance**: Validator's Definition of Done check rejects the spec
when attestation linkage is missing or incomplete.

### PR-F-008 — Attestation records reconstructable from repo

**Problem**: P1.

**Requirement**: Attestation records, ratification records, and
redaction records MUST be YAML files, one record per file, under
tenant-declared directory roots, with filenames
`<date>-<record-subject-id>.yml`. v0.1 MUST NOT introduce an external
attestation store.

**Traces to**: Feature 001 FR-004, FR-005, FR-016, FR-020, FR-020a.

**Acceptance**: An auditor with `git clone` alone resolves every
attestation field to repository content.

### PR-F-009 — Redaction gate blocks unredacted export

**Problem**: P1, P5.

**Requirement**: No tenant artifact MUST be treated as eligible for a
future public or NDA-visible export workflow unless a redaction record
exists naming source artifact, redacted regions, approver, and policy
version; redaction approvals are subject to author/approver
separation.

**Traces to**: Feature 001 FR-019, FR-020, FR-020a, FR-021.

**Acceptance**: v0.1 executes no export; the gate is enforced as a
metadata precondition.

### PR-F-010 — Assignment Envelope is the unit of agent work

**Problem**: P3.

**Requirement**: Every `/speckit-implement` invocation for a
Creator-Engine-governed batch MUST be inside a Hermes-authored
Assignment Envelope whose fields satisfy Feature 002 FR-005. Envelopes
are single-use; envelopes whose `allowed_mutation_classes` touch a
privileged class require Source ratification before consumption.

**Traces to**: Feature 002 FR-005, FR-006, FR-007, FR-008, FR-009,
FR-010, FR-011.

**Acceptance**: A reviewer can author one envelope by hand against a
hypothetical batch and confirm every FR-005 field is populated and
that author ≠ consumer.

### PR-F-011 — Parallel-agent work is governed, not prevented

**Problem**: P3.

**Requirement**: Creator Engine MUST permit multiple Hermes+Claude
pairs to work concurrently on different features, each in its own
worktree and branch under its own envelope, with canonical-branch
integration serialized and Source-ratified. One driver per physical
worktree.

**Traces to**: Feature 002 FR-015, FR-016; Feature 002 §Parallel-agent
development model (User Story 6).

**Acceptance**: A reviewer walks a two-pair scenario and confirms
neither pair overwrites the other's work and integration is
serialized.

### PR-F-012 — Conflict taxonomy covers four classes

**Problem**: P3, P4.

**Requirement**: Every observed conflict MUST be classifiable as
`textual`, `file/task ownership`, `semantic`, or `authority`; each
class names a detector, a resolver, and the evidence the resolution
must produce. `authority` conflicts hard-stop work and require Source
ratification.

**Traces to**: Feature 002 FR-017, FR-018.

**Acceptance**: A reviewer classifies the eight Edge Case scenarios in
Feature 002 §Edge Cases into one of the four classes and names the
resolver and evidence.

### PR-F-013 — Source-of-truth hierarchy is explicit

**Problem**: P4, P5.

**Requirement**: The source-of-truth hierarchy is constitution >
Feature 001 substrate (ratified) > Feature 002 canonical docs > tenant
fixtures > working notes. Feature 002 docs MUST defer to Feature 001
where they overlap and MUST flag dependencies on not-yet-shipped
features rather than inventing competing contracts.

**Traces to**: Feature 002 FR-019, FR-020, FR-021.

**Acceptance**: For any apparent conflict between artifacts at
different layers, an auditor can name which artifact wins and why.

### PR-F-014 — `/speckit-implement` policy is bound to the envelope

**Problem**: P3.

**Requirement**: `/speckit-implement` is the mandatory implementation
command for Creator-Engine-governed work and MUST be invoked only
inside a Hermes-authored Assignment Envelope. Out-of-envelope
invocation is an authority conflict requiring hard-stop and Source
ratification.

**Traces to**: Feature 002 FR-009, FR-010, FR-011.

**Acceptance**: The operating-model document
[`../architecture/agentic-sdlc-operating-model.md`](../architecture/agentic-sdlc-operating-model.md)
states the policy unambiguously and enumerates permitted and
prohibited actions.

### PR-F-015 — Canonical document set is exactly 17 documents

**Problem**: P1, P5.

**Requirement**: The canonical Creator Engine document set MUST be
exactly the 17 documents enumerated in Feature 002 §Canonical Document
Specifications; `docs/architecture/parallel-agent-development-model.md`
MUST remain separate from `docs/architecture/agentic-sdlc-operating-
model.md`.

**Traces to**: Feature 002 FR-022, FR-023, FR-024.

**Acceptance**: The 17 documents exist with non-empty required
sections; no extra canonical document path is invented.

## c. Non-functional product requirements

### PR-NF-001 — Auditability

Every governed mutation MUST be reconstructable from repository
artifacts alone: who proposed what, against which spec, with which
mutation class, with which evidence, ratified by whom.

**Traces to**: constitution Principle II, Principle VII, Principle
VIII; Feature 001 FR-005, FR-020a.

### PR-NF-002 — Repo-native v0.1

v0.1 MUST NOT introduce a hosted SaaS control plane, external policy
daemon, or non-repo state store. Every artifact MUST be
reconstructable from `git clone` alone.

**Traces to**: constitution Principle II; Feature 001 FR-005.

### PR-NF-003 — Offline validation

The validator MUST run from a fresh `git clone` without network
access. Installation MUST be possible from the checked-in wheelhouses
under `validators/wheelhouse/` and `validators/wheelhouse-dev/`.

**Traces to**: Feature 001 FR-026, FR-027a;
[`validators/README.md`](../../validators/README.md).

### PR-NF-004 — Spec Kit compatibility

Vanilla Spec Kit `spec.md`, `plan.md`, and `tasks.md` files MUST
remain byte-identical to vanilla Spec Kit; Creator Engine governance
metadata MUST live in adjacent sidecars.

**Traces to**: constitution Principle X; Feature 001 FR-009, FR-010,
FR-012a.

### PR-NF-005 — Tenant-agnosticism

Generic-contract paths (`docs/contracts/`, `schemas/`, `validators/`,
`templates/`) MUST contain no tenant-specific identifiers. Tenant
fixtures live under `tenants/<tenant>/`.

**Traces to**: constitution Principle IX; Feature 001 FR-024, FR-024a;
SC-004.

### PR-NF-006 — Security and privacy as design constraints

Security and privacy MUST be treated as design constraints rather than
afterthoughts. New mutation classes touching credentials, secrets,
identity, or external publication MUST declare their security/privacy
posture in the spec and be reviewed against that declaration at
ratification time.

**Traces to**: constitution Principle XII; Feature 001 FR-019–FR-021;
Feature 002 FR-008.

### PR-NF-007 — Constitution as gating reference

This product requirements catalog and every canonical doc MUST treat
the constitution at `.specify/memory/constitution.md` as the gating
reference. Conflicts with the constitution are resolved in favor of
the constitution.

**Traces to**: constitution §Authority & Boundaries.

## d. Explicit non-requirements

The following are NOT requirements of Creator Engine v0.1-docs:

- **CI automation and `.github/` content**: deferred to Feature 003.
- **Codex / QA / security governed identities and evidence schemas**:
  deferred to Feature 004.
- **Hermes dispatcher and worktree/sandbox runtime**: deferred to
  Feature 005.
- **Release records, deploy attestations, GitHub environments**:
  deferred to Feature 006.
- **Phase 2 autonomy expansion** (low-risk auto-merge, autonomous
  batch-pulling): not implemented; any Phase 2 promotion is a ratified
  amendment.
- **Hosted policy daemon, drift detection, dashboards, multi-tenant
  SaaS behavior**: out of scope per constitution Principle XI.
- **Public or NDA-visible export workflows**: gate defined; no export
  executed.
- **Tenant-specific assumptions in substrate artifacts**: forbidden by
  constitution Principle IX.

Naming these items as non-requirements does not preclude future
features. It records that v0.1 makes no implementation promise for
them and that any future feature that introduces them is itself a
Creator-Engine-governed spec.

## e. Traceability map

| Product req | Traces to (authoritative) |
|---|---|
| PR-F-001 | Feature 001 FR-001, FR-002, FR-003 |
| PR-F-002 | Feature 001 FR-009, FR-010, FR-012a, FR-012b; constitution Principle X |
| PR-F-003 | Feature 001 FR-006; Feature 002 §SDLC Transition Matrix |
| PR-F-004 | Feature 001 FR-008, FR-017, FR-018; Feature 002 FR-013 |
| PR-F-005 | Feature 001 FR-007; Feature 002 FR-006 |
| PR-F-006 | Feature 001 FR-013, FR-013a |
| PR-F-007 | Feature 001 FR-014, FR-013a; constitution Principle VII |
| PR-F-008 | Feature 001 FR-004, FR-005, FR-016, FR-020, FR-020a |
| PR-F-009 | Feature 001 FR-019, FR-020, FR-020a, FR-021 |
| PR-F-010 | Feature 002 FR-005–FR-011 |
| PR-F-011 | Feature 002 FR-015, FR-016, §Parallel-agent development model |
| PR-F-012 | Feature 002 FR-017, FR-018 |
| PR-F-013 | Feature 002 FR-019, FR-020, FR-021 |
| PR-F-014 | Feature 002 FR-009, FR-010, FR-011 |
| PR-F-015 | Feature 002 FR-022, FR-023, FR-024 |
| PR-NF-001 | constitution Principles II, VII, VIII; Feature 001 FR-005, FR-020a |
| PR-NF-002 | constitution Principle II; Feature 001 FR-005 |
| PR-NF-003 | Feature 001 FR-026, FR-027a |
| PR-NF-004 | constitution Principle X; Feature 001 FR-009, FR-010, FR-012a |
| PR-NF-005 | constitution Principle IX; Feature 001 FR-024, FR-024a |
| PR-NF-006 | constitution Principle XII; Feature 001 FR-019–FR-021; Feature 002 FR-008 |
| PR-NF-007 | constitution §Authority & Boundaries |

## Acceptance posture for this document

This REQUIREMENTS.md satisfies Feature 002 Canonical Document
Specification #4: every load-bearing PRD problem (P1–P5) has at least
one tracing entry; the traceability map links each product requirement
to a Feature 001 FR id, a Feature 002 FR id, or a Feature 002 section
anchor; the non-requirements section enumerates the automation surfaces
deferred per Feature 002 FR-025.
