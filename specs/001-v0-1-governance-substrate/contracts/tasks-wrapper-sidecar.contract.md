# Contract: Tasks Wrapper Sidecar (`tasks.creator-engine.yml`)

**Source FRs**: FR-012a, FR-012b

## Purpose

Adjacent YAML file that carries Creator Engine governance metadata for a
Spec Kit `tasks.md`. Provides per-task mutation class, permitted
actions, verification evidence references, and ratification/approval
references sufficient to enforce author/approver separation
(FR-007/FR-012b).

## Implementation surface

- `docs/contracts/tasks-wrapper-sidecar.md`
- `schemas/tasks-wrapper-sidecar.schema.yaml`
- `templates/tasks.creator-engine.template.yaml`

## Required fields (top-level)

`spec_ref`, `tasks` (non-empty array of TaskEntry).

## TaskEntry fields

`id` (unique within sidecar), `title`, `mutation_class`,
`permitted_actions`, `verification_evidence_ref`, `author_actor_id`.
Optional: `ratification_or_approval_ref` (required for
ratification-relevant tasks), `approver_actor_id` (when an approver
is named at task time, MUST NOT equal `author_actor_id` per FR-007).

## Validator checks

- `sidecar_conformance.py`: schema-level field presence and types.
- `mutation_class.py`: per-task class/action mismatch detection
  (FR-027a; spec edge-case "a docs class mutation that modifies
  governance files").
- `ratification.py`: per-task `approver_actor_id ≠ author_actor_id`
  when both present (FR-007).
- Cross-artifact: every `verification_evidence_ref` resolves to an
  existing path or anchor (FR-014: rejects self-claims of
  completion).

## Acceptance evidence

- Tasks-level wrapper conformance is verified end-to-end in
  examples/well-formed and examples/malformed/tasks.creator-
  engine.class-action-mismatch.yml (FR-029).
