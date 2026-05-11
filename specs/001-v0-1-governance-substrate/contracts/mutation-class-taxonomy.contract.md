# Contract: Mutation Class Taxonomy

**Source FRs**: FR-006, FR-007, FR-008

## Purpose

Defines the named categories of governed work and the action vocabulary
each category permits. v0.1 ships nine mandatory baseline classes and a
reserved-action vocabulary; tenants MAY overlay extension classes
without redefining baseline semantics.

## Implementation surface

- `docs/contracts/mutation-class-taxonomy.md` — human-readable
  description of the baseline classes, the reserved-action
  vocabulary, and the FR-008 privileged-class rules.
- `schemas/mutation-class.schema.yaml` — JSON Schema for class
  declarations (used both for the substrate baseline and for tenant
  extension files).

## Baseline classes (mandatory in every tenant)

`docs`, `code`, `schema`, `deploy`, `governance`, `identity`,
`security`, `attestation`, `redaction`.

## Reserved-action vocabulary

`propose`, `edit`, `commit`, `open_pr`, `attest`, `advise_only`,
`merge`, `deploy`, `publish`, `issue_credential`,
`revoke_credential`, `alter_org_settings`, `alter_tenant_settings`,
`alter_repo_settings`, `approve_redaction`,
`weaken_attestation_gate`, `weaken_redaction_gate`.

## Privileged-class rule (FR-008)

For classes touching merge, deploy, publish/export, credential
issuance/revocation, organization/tenant/repo settings, governance,
security, identity, attestation-gate weakening, or redaction-gate
weakening, the taxonomy MUST set
`human_ratification_required: true`, and `agent_permitted_actions`
MUST NOT include any of the reserved actions named above.

## Tenant-extension rule (FR-006)

Tenant extension classes set `is_baseline: false`, MUST NOT reuse a
baseline class name, MUST draw `action_vocabulary` entries from the
reserved-action vocabulary above, and MUST NOT redefine baseline
class semantics.

## Validator checks

- `mutation_class.py`:
  - All nine baseline classes are present and conform to the
    privileged-class rule.
  - Tenant extension classes do not reuse baseline names.
  - Every `action_vocabulary` and `agent_permitted_actions` entry is
    in the reserved-action vocabulary.
  - Class/action mismatch detection across spec/plan/tasks sidecars
    (FR-027a; spec edge-case).

## Acceptance evidence

- Spec User Story 3, Acceptance Scenarios 1–4.
- Spec edge-case "A mutation whose declared mutation class does not
  permit the actions taken (for example, a `docs` class mutation that
  modifies governance files)".
