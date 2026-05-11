# Contract: Mutation Class Taxonomy

Source FRs: FR-006, FR-007, FR-008
Validator check: `mutation_class` (deferred to sub-batch A2)
Schema: `schemas/mutation-class.schema.yaml`
Baseline data: `docs/contracts/mutation-class-taxonomy.yml`

## Purpose

A Mutation Class names a category of governed work and the action
vocabulary the substrate permits an agent or human to take under it.
Every executable Creator Engine work item declares its mutation class;
declarations that fall outside the taxonomy or that exceed the
class's permitted actions are contract violations surfaced by the
validator.

The substrate ships nine mandatory baseline classes:

- `docs`
- `code`
- `schema`
- `deploy`
- `governance`
- `identity`
- `security`
- `attestation`
- `redaction`

Tenants MAY declare additional extension classes in
`tenants/<name>/mutation-classes.yml`; tenant extensions MUST NOT
reuse a baseline name and MUST NOT redefine baseline semantics. The
v0.1 baseline class set is mandatory in every tenant.

## Reserved-action vocabulary (FR-006)

Every `action_vocabulary` and `agent_permitted_actions` entry — for
baseline classes and tenant extensions alike — MUST be drawn from this
v0.1 reserved-action vocabulary:

| Action | Reserved-restricted? | Notes |
|---|---|---|
| `propose` | no | Author a proposal artifact (spec, plan, task). |
| `edit` | no | Modify an existing artifact. |
| `commit` | no | Create a git commit on a working branch. |
| `open_pr` | no | Open a pull request for review. |
| `attest` | no | Author an attestation record. |
| `advise_only` | no | Provide review or advisory text without authoring change. |
| `merge` | **yes** | Merge a pull request to a protected branch. |
| `deploy` | **yes** | Deploy or release a build to any environment. |
| `publish` | **yes** | Publish artifacts publicly or to NDA-visible distribution. |
| `issue_credential` | **yes** | Create or rotate credentials, tokens, or secrets. |
| `revoke_credential` | **yes** | Revoke credentials, tokens, or secrets. |
| `alter_org_settings` | **yes** | Change organization-level settings on the source host. |
| `alter_tenant_settings` | **yes** | Change tenant-level governance settings. |
| `alter_repo_settings` | **yes** | Change repository-level settings on the source host. |
| `approve_redaction` | **yes** | Approve a redaction record under FR-019..FR-021. |
| `weaken_attestation_gate` | **yes** | Modify the attestation gate to reduce its strictness. |
| `weaken_redaction_gate` | **yes** | Modify the redaction gate to reduce its strictness. |

Coining a new action outside this vocabulary is a contract-breaking
change requiring a v0.2 governance amendment. Tenant extensions MUST
NOT introduce new actions; they may only reuse those listed above.

## FR-008 privileged-class rule (Reading A strict)

Source approved Reading A on 2026-05-10. Under Reading A:

1. **No baseline class's `agent_permitted_actions` may include any
   reserved-restricted action.** This rule is universal across the
   nine baseline classes regardless of `human_ratification_required`.
   Reserved-restricted actions are reserved for the ratification flow
   (forthcoming `docs/contracts/ratification-flow.md`) and the
   authority matrix (`docs/contracts/authority-matrix.md`); they are
   not unlocked for agents by setting `human_ratification_required:
   true`.

2. **Privileged baseline classes** — `deploy`, `governance`,
   `identity`, `security`, `attestation`, `redaction` — MUST set
   `human_ratification_required: true`. The schema enforces this as a
   per-class invariant.

3. The `human_ratification_required` flag is a marker that human
   ratification is required *somewhere in the lifecycle*; it is
   evaluated together with the authority matrix and the ratification
   flow at sub-batch B / US3 ratification time. It does not weaken
   rule (1).

The reserved-restricted action set, made explicit:

`merge`, `deploy`, `publish`, `issue_credential`, `revoke_credential`,
`alter_org_settings`, `alter_tenant_settings`, `alter_repo_settings`,
`approve_redaction`, `weaken_attestation_gate`,
`weaken_redaction_gate`.

## Per-class declaration shape

Each entry in `mutation-class-taxonomy.yml` and in tenant overlays
MUST have:

| Field | Type | FR | Rule |
|---|---|---|---|
| `name` | string | FR-006 | kebab-case slug `^[a-z][a-z0-9-]*$`; for baseline entries, one of the nine baseline names; tenant extensions MUST NOT reuse a baseline name |
| `is_baseline` | boolean | FR-006 | `true` for the nine baseline entries; `false` for tenant extensions |
| `description` | string | FR-006 | non-empty rationale; reviewers consult this to judge what work belongs in the class |
| `action_vocabulary` | array<string> | FR-006 | non-empty; every item drawn from the reserved-action vocabulary; values unique within the array |
| `agent_permitted_actions` | array<string> | FR-006/FR-008 | every item drawn from the reserved-action vocabulary; values unique within the array; under Reading A, MUST NOT contain any reserved-restricted action; the validator additionally enforces that this is a subset of `action_vocabulary` (see "Validator behavior" below) |
| `human_ratification_required` | boolean | FR-006/FR-008 | `true` for the privileged baseline classes (`deploy`, `governance`, `identity`, `security`, `attestation`, `redaction`); other baseline classes set `false` |

## Tenant extension overlay rule

Tenant extensions live in `tenants/<name>/mutation-classes.yml` and
validate against the same `schemas/mutation-class.schema.yaml`.
Extensions:

- set `is_baseline: false`;
- MUST NOT reuse a baseline `name` (validator: FR-006 violation);
- MUST draw `action_vocabulary` and `agent_permitted_actions` items
  from the substrate's reserved-action vocabulary;
- MUST NOT redefine baseline class semantics (the substrate's
  baseline file is canonical; extensions cannot shadow or modify it);
- MUST satisfy the same Reading A reserved-restricted-action
  exclusion in `agent_permitted_actions`.

The `mutation_class` validator (sub-batch A2) loads the baseline file
plus any tenant overlays and asserts: (a) all nine baselines are
present, (b) no extension reuses a baseline name, (c) every entry's
`agent_permitted_actions` is a subset of its own
`action_vocabulary`, (d) Reading A holds across all entries.

## Class/action mismatch detection (FR-027a)

The mutation_class validator (sub-batch A2) cross-checks every
spec-, plan-, and tasks-sidecar's declared `mutation_class` and
`permitted_actions` against this taxonomy. A `permitted_actions`
value not present in the declared class's `action_vocabulary`, or a
class name not declared in this taxonomy or any tenant overlay, is a
class/action mismatch reported with FR-006/FR-027a citations.

The spec edge case "a `docs` class mutation that modifies governance
files" is the canonical example: a tasks-sidecar entry declaring
`mutation_class: docs` but a `permitted_actions` set that the
validator's policy reads as inconsistent with `docs` (e.g., touching
governance contract paths) is flagged at sub-batch B / US4 cross-
checks. The substrate's v0.1 enforcement is shape- and vocabulary-
based; semantic file-path classification is an A2/B concern.

## Validator behavior

The `mutation_class` check (sub-batch A2) cites this contract on
every failure per FR-027:

- baseline class missing: `FR-006: tenants/<name>/mutation-classes.yml: baseline class <name> missing (consult docs/contracts/mutation-class-taxonomy.md)`
- tenant extension reuses baseline name: `FR-006: <path>: tenant extension reuses baseline class name <name> (consult docs/contracts/mutation-class-taxonomy.md)`
- action outside reserved vocabulary: `FR-006: <path>: action <action> is not in the reserved-action vocabulary (consult docs/contracts/mutation-class-taxonomy.md)`
- agent_permitted_actions exceeds action_vocabulary: `FR-006: <path>: agent_permitted_actions item <action> not declared in action_vocabulary (consult docs/contracts/mutation-class-taxonomy.md)`
- Reading A violation: `FR-008: <path>: agent_permitted_actions includes reserved-restricted action <action> under Reading A (consult docs/contracts/mutation-class-taxonomy.md)`
- privileged class missing human ratification flag: `FR-008: <path>: privileged class <name> requires human_ratification_required: true (consult docs/contracts/mutation-class-taxonomy.md)`
- class/action mismatch in a sidecar: `FR-006/FR-027a: <sidecar>: permitted_actions item <action> not in action_vocabulary of declared class <name> (consult docs/contracts/mutation-class-taxonomy.md)`
