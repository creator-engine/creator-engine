# Contract: Authority Matrix

**Source FRs**: FR-015

## Purpose

For each generic role category, names the allowed instruction sources,
allowed mutation classes, required ratifier, allowed communication
surfaces, and required audit artifacts. The matrix MUST contain
concrete rows for every baseline mutation class. Tenant-specific role
names are overlay-only.

## Implementation surface

- `docs/contracts/authority-matrix.md` — human-readable matrix with
  one concrete row per baseline mutation class and one row per role
  category.
- `schemas/authority-matrix.schema.yaml` — JSON Schema for matrix
  rows (used both for the substrate baseline and for tenant overlays
  at `tenants/<name>/authority-matrix-overlay.yml`).

## Role categories (v0.1)

`source`, `ratifier`, `reviewer`, `architect`, `implementer`,
`verifier`, `observer`.

## Per-row required fields

`role_category`, `allowed_instruction_sources`,
`allowed_mutation_classes`, `required_ratifier_role`,
`allowed_communication_surfaces`, `required_audit_artifacts`.
Tenant overlays MAY add `tenant_role_name` to alias a baseline role
under a tenant-specific name.

## Validator checks

- Schema validation of every row.
- Coverage check: every baseline mutation class is referenced in at
  least one matrix row's `allowed_mutation_classes`.
- For FR-008 privileged classes, `required_ratifier_role` resolves to
  a row whose `role_category` is a human role.
- `no_limitless_strings.py`: the generic
  `docs/contracts/authority-matrix.md` and
  `schemas/authority-matrix.schema.yaml` contain zero LIMITLESS
  identifiers (FR-024, SC-004); LIMITLESS-specific role aliases live
  only in `tenants/limitless/authority-matrix-overlay.yml`.

## Acceptance evidence

- Spec User Story 3, Acceptance Scenario 1 (reviewer can read off
  every role's allowed sources/classes/ratifier/surfaces/artifacts).
