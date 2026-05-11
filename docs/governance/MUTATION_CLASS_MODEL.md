# Creator Engine Mutation Class Model

**Status**: Canonical. Authored under Sprint 0 Execution Slice A.

**Source-of-truth relationship**: SUMMARY. The authoritative source for
the mutation-class taxonomy, the reserved-action vocabulary, the
tenant-extension overlay rule, and the privileged-class ratification
rule is the Feature 001 contract at
[`../contracts/mutation-class-taxonomy.md`](../contracts/mutation-class-taxonomy.md),
together with the schema at `schemas/mutation-class.schema.yaml` and
the baseline data at `docs/contracts/mutation-class-taxonomy.yml`.
This document summarizes that contract and explains how the operating
model (Feature 002) consumes it. It MUST NOT redefine the baseline
classes or the action vocabulary.

## a. Baseline class summary (Feature 001 FR-006)

The substrate ships exactly nine mandatory baseline classes. Each is
mandatory in every tenant. Tenants MAY declare additional classes via
overlay (`tenants/<name>/mutation-classes.yml`); tenant extensions
MUST NOT reuse a baseline name or redefine baseline semantics.

| Baseline class | Privileged? | Description (per Feature 001 contract) |
|---|---|---|
| `docs` | No | Documentation, narrative, and non-contract repository content. |
| `code` | No | Application/library source code and accompanying tests. |
| `schema` | No | Substrate or tenant schemas — the typed shape contracts. |
| `deploy` | Yes | Deploy or release a build to any environment. |
| `governance` | Yes | Changes to governance rules, authority matrix, contracts. |
| `identity` | Yes | Creation, rotation, or revocation of governed identities. |
| `security` | Yes | Changes to security or redaction policy. |
| `attestation` | Yes | Changes to attestation gate, attestation schema. |
| `redaction` | Yes | Changes to redaction gate, redaction policy, redaction record. |

The six privileged classes are enumerated in Feature 001 FR-008 and
re-anchored in this operating-model layer at Feature 002 FR-013 and
FR-017.

## b. Reserved-action vocabulary (Feature 001 FR-006)

Every `action_vocabulary` and `agent_permitted_actions` entry — for
baseline classes and tenant extensions alike — MUST be drawn from this
v0.1 reserved-action vocabulary. The "reserved-restricted" column
restates the table at
[`../contracts/mutation-class-taxonomy.md`](../contracts/mutation-class-taxonomy.md)
without modification.

| Action | Reserved-restricted? |
|---|---|
| `propose` | No |
| `edit` | No |
| `commit` | No |
| `open_pr` | No |
| `attest` | No |
| `advise_only` | No |
| `merge` | Yes |
| `deploy` | Yes |
| `publish` | Yes |
| `issue_credential` | Yes |
| `revoke_credential` | Yes |
| `alter_org_settings` | Yes |
| `alter_tenant_settings` | Yes |
| `alter_repo_settings` | Yes |
| `approve_redaction` | Yes |
| `weaken_attestation_gate` | Yes |
| `weaken_redaction_gate` | Yes |

Coining a new action outside this vocabulary is a contract-breaking
change requiring a v0.2 governance amendment. Tenant extensions MUST
reuse only the actions in this table.

## c. Tenant-extension overlay policy (Feature 001 FR-006)

Tenant extensions live in `tenants/<name>/mutation-classes.yml` and
validate against the same `schemas/mutation-class.schema.yaml`.
Extensions:

- set `is_baseline: false`;
- MUST NOT reuse a baseline `name`;
- MUST draw `action_vocabulary` and `agent_permitted_actions` items
  from the reserved-action vocabulary in §b;
- MUST NOT redefine baseline class semantics;
- MUST satisfy the Reading A reserved-restricted-action exclusion in
  `agent_permitted_actions` (no baseline class's agent-permitted
  actions may contain a reserved-restricted action).

A tenant cannot bypass the privileged-class ratification rule by
declaring a non-privileged "alias" extension class whose semantics
shadow a privileged class. The class/action mismatch detector (Feature
001 FR-027a) and the authority-matrix check together catch this.

## d. Privileged-class ratification rules (Feature 001 FR-008)

Source approved Reading A on 2026-05-10 and ratified it in the
substrate contract:

1. **No baseline class's `agent_permitted_actions` may include any
   reserved-restricted action.** This applies universally across all
   nine baseline classes. Reserved-restricted actions are reserved for
   the ratification flow (Feature 001
   `docs/contracts/ratification-flow.md`) and the authority matrix
   (`docs/contracts/authority-matrix.md`); they are not unlocked for
   agents by setting `human_ratification_required: true`.
2. **Privileged baseline classes** (`deploy`, `governance`, `identity`,
   `security`, `attestation`, `redaction`) MUST set
   `human_ratification_required: true`.
3. The `human_ratification_required` flag is a marker that human
   ratification is required somewhere in the lifecycle; it is
   evaluated together with the authority matrix and the ratification
   flow at ratification time. It does not weaken rule 1.

Operating-model implications of these rules:

- Agent-authored review text (Codex, future QA agent, future security
  agent) MUST NOT count as ratification for any privileged class
  (Feature 001 FR-017; Feature 002 FR-013).
- CI MUST NOT ratify any privileged class; CI is mechanical
  validation and produces evidence, not ratification (Feature 002
  FR-013; SDLC Transition Matrix transition T17).
- A "go ahead" message on a surface that the ratification flow has not
  designated as a valid ratification surface for the relevant
  mutation class does NOT authorize merge, deploy, publish, or any
  other reserved-restricted action (Feature 001 FR-018).
- Changes to CI policy, branch protection, deploy automation, or
  `.github/` content are themselves privileged
  `governance`/`security`/`deploy`-class mutations per Feature 001
  FR-008 and require Source ratification.

## e. Usage in Assignment Envelopes (Feature 002 FR-005)

The Assignment Envelope is the governed unit of agent work and is
where the mutation-class taxonomy meets `/speckit-implement`.

- `allowed_mutation_classes` MUST be drawn from the baseline taxonomy
  in §a plus any ratified tenant extensions; it MUST NOT include a
  class that the active tenant's overlay has not declared.
- Where `allowed_mutation_classes` declares any privileged class (per
  §d), the envelope itself MUST be Source-ratified before any consumer
  may begin work (Feature 002 FR-008).
- An agent (Claude Code in v0.1, future QA/security/release agents
  per Feature 004 / Feature 006) MUST operate strictly within the
  envelope's `allowed_mutation_classes`; expanding the class set
  unilaterally is an authority conflict (Feature 002 FR-018) and
  hard-stops work.
- `prohibited_surfaces` is the path/glob counterpart of the class
  restriction: even within an allowed class, a path declared
  prohibited MUST NOT be mutated.

The envelope authority interaction is enforced at three layers:

1. **Author/approver separation**: `created_by_actor_id` (Hermes role)
   MUST be distinct from `consuming_actor_id` (implementer role) per
   Feature 002 FR-006.
2. **Single-use**: an envelope whose stop conditions have been
   satisfied MUST NOT be reused (Feature 002 FR-007).
3. **Privileged-class gating**: privileged-class envelopes MUST be
   Source-ratified before consumption (Feature 002 FR-008).

A spec is not a substitute for an envelope and an envelope is not a
substitute for a spec; both are required for governed agent work.

## f. Usage in the SDLC Transition Matrix (Feature 002 normative matrix)

The SDLC state machine ties mutation classes to gates and Phase 1 /
Phase 2 labels. The normative matrix lives in
[`../architecture/agentic-sdlc-operating-model.md`](../architecture/agentic-sdlc-operating-model.md)
and the source spec at
`specs/002-canonical-docs-and-operating-model/spec.md` §SDLC
Transition Matrix. Below summarizes how the mutation classes constrain
key transitions; the matrix is authoritative.

- **T3, T5 (PRD Drafted → Ratified; Architecture Drafted → Ratified)**:
  PRD and architecture ratification are `governance`-class privileged
  mutations; Source is the ratifier. Remains Phase 1.
- **T10 (Tasks Generated → Batch Approved)**: scope review against the
  mutation-class taxonomy. Privileged-class batches are Source-only
  per FR-008; non-privileged-class batches MAY use a Source-delegated
  ratifier per the Feature 001 authority matrix once delegation is
  ratified.
- **T13 (Worktree Created → Implementation Complete)**: Claude Code
  may only mutate inside the envelope's `allowed_mutation_classes` and
  outside its `prohibited_surfaces`. Privileged-class envelopes
  require prior Source ratification (FR-008).
- **T15 (Local Validation Complete → Attestation Drafted)**:
  drafting/finalizing attestation is itself an `attestation`-class
  privileged mutation; Hermes drafts and Source ratifies. Remains
  Phase 1.
- **T16 (Attestation Drafted → Independent Review Complete)**: Codex
  review evidence is recorded as `docs`-class review evidence; review
  evidence is NEVER ratification for privileged classes (FR-013,
  FR-017).
- **T17 (Independent Review Complete → CI Evidence Complete)**: CI
  pass produces evidence, not classified mutation; changes to CI
  policy or `.github/` are themselves privileged.
- **T19 (Scope Audit Complete → Ratification Complete)**: ratification
  decision recorded against the mutation class. Privileged classes
  Source-only.
- **T22 (Release Candidate Created → Deployment Approved)**: deploy
  ratification — `deploy` class is privileged and Source-only. Remains
  Phase 1.
- **T23 (Deployment Approved → Deployment Complete)**: deploy
  execution by the future release agent (Feature 006 deferral); the
  release agent never ratifies the `deploy` class.

## g. Validator behavior (Feature 001 FR-027a)

The `mutation_class` check is part of the Creator Engine validator
runnable from a fresh `git clone` per
[`validators/README.md`](../../validators/README.md). It surfaces:

- baseline class missing from a tenant overlay;
- tenant extension reusing a baseline name;
- action outside the reserved vocabulary;
- `agent_permitted_actions` containing an action not declared in the
  class's `action_vocabulary`;
- Reading A violation (`agent_permitted_actions` including a
  reserved-restricted action);
- privileged class missing `human_ratification_required: true`;
- class/action mismatch in any spec, plan, or tasks sidecar.

Each violation cites the contract at
[`../contracts/mutation-class-taxonomy.md`](../contracts/mutation-class-taxonomy.md)
per Feature 001 FR-027.

## Acceptance posture for this document

This MUTATION_CLASS_MODEL.md satisfies Feature 002 Canonical Document
Specification #11: the baseline class list matches Feature 001 FR-006
exactly; the privileged-class list matches FR-008 exactly; usage in
Assignment Envelopes cites Feature 002 FR-005 and the SDLC Transition
Matrix; the document summarizes and applies the Feature 001 contract
without redefining the baseline classes or the action vocabulary.
