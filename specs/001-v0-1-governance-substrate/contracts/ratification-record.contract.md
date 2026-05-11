# Contract: Ratification Record

**Source FRs**: FR-016, FR-017, FR-018, FR-020a

## Purpose

Records who ratified a mutation, on which surface, against which spec
and mutation class, with what evidence reviewed. Co-located with the
attestation record by `mutation_id` so an auditor can join the two
artifacts deterministically.

## Implementation surface

- `docs/contracts/ratification-record.md`
- `schemas/ratification-record.schema.yaml`
- `templates/ratification-record.template.yaml`

## File location and naming (FR-020a)

Under the tenant's `ratification_storage_path`. Filename
`<YYYY-MM-DD>-<mutation_id>.yml`. One record per ratification.

## Required fields

`mutation_id`, `spec_ref`, `mutation_class`, `ratifier_actor_id`,
`ratifier_role`, `surface`, `evidence_reviewed`, `decision`
(`accept` in v0.1), `created_at`.

## Validator checks

- `ratification.py`:
  - `ratifier_actor_id` ≠ spec author actor (FR-007).
  - `surface` ∈ ratification flow's
    `valid_ratification_surfaces` for `mutation_class`.
  - For FR-008 privileged classes, `ratifier_actor_id` is human (not
    an agent identity).
  - `mutation_id` joins to exactly one Attestation Record.

## Acceptance evidence

- Spec User Story 3, Acceptance Scenarios 2–4.
- Spec edge-case "A redaction approval performed by the same actor
  who authored the underlying tenant artifact" — same author/approver
  separation logic enforced for ratification.
