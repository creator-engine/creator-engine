# Contract: Redaction Gate Policy

**Source FRs**: FR-019, FR-020, FR-021

## Purpose

Negative policy gate: no tenant artifact may be eligible for any future
public or NDA-visible export workflow unless a Redaction Record exists
that lists what was redacted, who approved the redaction, and against
which redaction policy version. v0.1 defines the policy and validator
behavior only; v0.1 does NOT execute any export workflow.

## Implementation surface

- `docs/contracts/redaction-gate-policy.md` — human-readable policy,
  including the FR-021 author/approver separation rule for redaction
  approvers.

## Policy fields

`policy_version`, `applies_to_export_intents` (subset of `public`,
`nda_visible`), `required_redaction_outputs`, `approver_constraints`.

## Validator checks

- `redaction_gate.py`:
  - Any artifact declaring `export_intent: public` or
    `export_intent: nda_visible` MUST reference a Redaction Record
    bound to a known `policy_version`.
  - The redaction approver MUST NOT equal the underlying artifact's
    author (FR-021).

## Acceptance evidence

- Spec User Story 5, Acceptance Scenarios 1–3.
- SC-009: 0 tenant artifacts that declare future public/NDA-visible
  export intent are treated as eligible without a Redaction Record.
