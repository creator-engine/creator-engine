# Contract: Spec Wrapper Sidecar (`spec.creator-engine.yml`)

**Source FRs**: FR-009, FR-010, FR-011, FR-012, FR-012a

## Purpose

Adjacent YAML file that carries Creator Engine governance metadata for a
Spec Kit `spec.md`, without modifying the Spec Kit file itself. The
sidecar is the canonical source for governance fields; vanilla Spec
Kit display fields (e.g. title) are compatibility metadata only.

## Implementation surface

- `docs/contracts/spec-wrapper-sidecar.md` — human-readable contract,
  including the FR-009 compatibility-vs-canonical rule and the
  one-feature-folder adjacency rule (research Decision 4).
- `schemas/spec-wrapper-sidecar.schema.yaml` — JSON Schema enforcing
  field presence, the six-state `status` enum (FR-013a), and the
  seven-member `spec_type` enum (FR-011).
- `templates/spec.creator-engine.template.yaml` — project-agnostic
  template.

## Required fields

`id`, `title`, `tenant`, `owner_role`, `status`, `spec_type`,
`mutation_class`, `permitted_actions`, `scope`, `acceptance_criteria`,
`verification`, `ratification_required`, `identity_policy_ref`.
Conditional fields: `attestation_record_ref` (required at status
`verified` or beyond), `ratification_record_ref` (required at status
`ratified` or beyond).

## Validator checks

- `sidecar_conformance.py`: schema-level field presence, type, enum
  membership.
- `duplicate_spec_id.py`: `id` uniqueness across the repo (FR-027a;
  spec edge-case "Two governed specs declaring the same id").
- `definition_of_ready.py`: scope/acceptance/verification non-empty
  for status ≥ `ready` (FR-013).
- `mutation_class.py`: `permitted_actions` ⊆ class action vocabulary
  (FR-006/FR-027a class/action mismatch detection).
- `lifecycle.py`: status enum value and transition gates per
  data-model.md State Transitions section.

## Compatibility rule (FR-009)

If a vanilla Spec Kit `spec.md` carries display metadata that
materially disagrees with the sidecar value for the same field, the
validator emits a `WARN` or `FAIL` per the field's schema rule. The
sidecar value is canonical; silent override is forbidden.

## Acceptance evidence

- Spec User Story 2, Acceptance Scenarios 1–4.
- US2 AS4 explicitly verifies Spec Kit byte-identical compatibility
  (principle X).
