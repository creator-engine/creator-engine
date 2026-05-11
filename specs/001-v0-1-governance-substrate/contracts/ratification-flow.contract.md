# Contract: Ratification Flow

**Source FRs**: FR-016, FR-017, FR-018

## Purpose

Per mutation class, names which role(s) MUST ratify, which surfaces
count as valid ratification surfaces, and what evidence the ratifier
reviews. Encodes the rule that a "go ahead" message in any
non-designated surface is NOT ratification.

## Implementation surface

- `docs/contracts/ratification-flow.md` — generic ratification flow
  rules, including the FR-017 split between agent-recordable review
  evidence and human ratification.
- Tenant-specific surface names live in
  `tenants/<name>/ratification-flow.yml`.

## Per-flow-entry fields

`mutation_class`, `required_ratifier_role`,
`valid_ratification_surfaces`, `evidence_required`.

## Validator checks

- `ratification.py`:
  - For every spec at status `ratified` or `done`, a Ratification
    Record exists at the tenant's `ratification_storage_path`.
  - The record's `surface` matches a `valid_ratification_surfaces`
    entry for the spec's mutation class.
  - The ratifier actor is distinct from the spec's author actor
    (FR-007).
  - For FR-008 privileged classes, the ratifier MUST be a human
    (FR-017): agent-authored review text MUST NOT be recorded as
    ratification for those classes.
  - "Go ahead" messages on un-designated surfaces are NOT accepted
    as ratification (FR-018; spec edge-case).

## Acceptance evidence

- Spec User Story 3, Acceptance Scenarios 2–4.
- Spec edge-case "A 'go ahead' in a chat surface that the matrix
  does not designate".
