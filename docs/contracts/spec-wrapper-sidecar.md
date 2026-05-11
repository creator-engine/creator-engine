# Contract: Spec Wrapper Sidecar

Source FRs: FR-009, FR-010, FR-011, FR-012, FR-012a, FR-013, FR-013a, FR-027a
Canonical filename: `spec.creator-engine.yml`
Schema: `schemas/spec-wrapper-sidecar.schema.yaml`
Validator checks: `sidecar_conformance`, `duplicate_spec_id`, `definition_of_ready`

## Purpose

A Spec Wrapper Sidecar is the Creator Engine governance wrapper for a
vanilla Spec Kit `spec.md`. It lives beside `spec.md` and carries the
machine-readable governance fields used by Creator Engine validation.
The Spec Kit Markdown file remains vanilla Markdown; governance metadata
MUST NOT be moved into the body or native frontmatter.

## Sidecar discovery rule (FR-012a)

For any governed Spec Kit spec file, the sidecar is discovered by directory
adjacency:

- Spec Kit file: `spec.md`
- Creator Engine sidecar: `spec.creator-engine.yml`

The sidecar MUST be in the same directory as `spec.md`. The Markdown file
MUST NOT be renamed or restructured to carry Creator Engine fields.

## Compatibility-vs-canonical rule (FR-009)

Creator Engine treats the sidecar as canonical for governance fields.
Native Spec Kit fields, such as title or status in Markdown frontmatter,
are display/compatibility metadata only. If a native Spec Kit display field
and the corresponding sidecar field are both present but materially
disagree, the validator reports a consistency warning or failure. It MUST
NOT silently choose one value.

## Required fields

| Field | Type | FR | Rule |
|---|---|---|---|
| `id` | string | FR-009/FR-027a | non-empty and unique across all spec sidecars |
| `title` | string | FR-009 | non-empty governance title |
| `tenant` | string | FR-009 | resolves to a tenant identity record in later cross-artifact checks |
| `owner_role` | string | FR-009 | generic role category or tenant overlay role |
| `status` | enum | FR-013a | exactly `draft`, `ready`, `in_progress`, `verified`, `ratified`, or `done` |
| `spec_type` | enum | FR-011 | one of the seven v0.1 spec types listed below |
| `mutation_class` | string | FR-012a | declared mutation class name |
| `permitted_actions` | array<string> | FR-012a | actions permitted for this spec's class |
| `scope` | string | FR-013 | non-empty before status may be `ready` or beyond |
| `acceptance_criteria` | array<string> | FR-013 | non-empty before status may be `ready` or beyond |
| `verification` | object | FR-013 | contains `method` and `evidence_refs` before status may be `ready` or beyond |
| `ratification_required` | boolean | FR-012a | whether explicit ratification is required |
| `identity_policy_ref` | string | FR-009 | repo-relative reference to the identity record governing this spec |

Optional lifecycle linkage fields:

- `attestation_record_ref`: repo-relative attestation record path.
- `ratification_record_ref`: repo-relative ratification record path.

## Spec type taxonomy (FR-011)

The v0.1 taxonomy is exactly:

- `decision_record`
- `implementation_spec`
- `research_report`
- `handoff`
- `retro`
- `test_spec`
- `tenant_config`

Unknown types are rejected rather than silently accepted.

## Definition of Ready hook (FR-013)

For `status` values `ready`, `in_progress`, `verified`, `ratified`, or
`done`, the `scope`, `acceptance_criteria`, and `verification` fields MUST
be present and non-empty. The `definition_of_ready` check reports missing
or empty fields as FR-013 violations.

## Duplicate id rule (FR-027a)

Every `id` across discoverable spec sidecars MUST be unique. The
`duplicate_spec_id` check reports every duplicate with the duplicate value
and paths to the colliding sidecars.
