# Contract: Redaction Record

**Source FRs**: FR-020, FR-020a, FR-021

## Purpose

Records the artifact-level redaction approval: source artifact,
redacted regions, approver, and redaction policy version applied.

## Implementation surface

- `docs/contracts/redaction-record.md`
- `schemas/redaction-record.schema.yaml`
- `templates/redaction-record.template.yaml`

## File location and naming (FR-020a)

Under the tenant's `redaction_storage_path`. Filename
`<YYYY-MM-DD>-<redaction_id-or-artifact_id>.yml`. One record per
redaction.

## Required fields

`redaction_id`, `source_artifact_ref`, `redacted_regions[]`
(each with `path`, `locator`, `reason`), `approver_actor_id`,
`approver_role`, `policy_version`, `created_at`.

## Validator checks

- `redaction_gate.py`:
  - `approver_actor_id` ≠ source artifact's author (FR-021).
  - `policy_version` resolves to a known Redaction Gate Policy
    version.
  - All `redacted_regions[].path` references resolve.

## Acceptance evidence

- Spec User Story 5, Acceptance Scenarios 1–3.
- Spec edge-case "A redaction approval performed by the same actor
  who authored the underlying tenant artifact".
