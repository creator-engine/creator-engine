# Contract: Plan Wrapper Sidecar (`plan.creator-engine.yml`)

**Source FRs**: FR-012a, FR-012b

## Purpose

Adjacent YAML file that carries Creator Engine governance metadata for a
Spec Kit `plan.md`, including the plan-level mutation-class summary, the
plan-level permitted-actions summary, the plan's verification approach,
ratification requirement, and identity reference.

## Implementation surface

- `docs/contracts/plan-wrapper-sidecar.md`
- `schemas/plan-wrapper-sidecar.schema.yaml`
- `templates/plan.creator-engine.template.yaml`

## Required fields

`spec_ref`, `plan_mutation_class_summary`,
`plan_permitted_actions_summary`, `verification_plan`,
`ratification_required`, `identity_policy_ref`.

## Validator checks

- `sidecar_conformance.py`: schema-level field presence and types.
- `mutation_class.py`: every class in `plan_mutation_class_summary`
  is declared and the plan-level permitted actions are a subset of
  the union of those classes' action vocabularies.
- Cross-artifact: `spec_ref` resolves to an existing spec sidecar
  whose `mutation_class` is among `plan_mutation_class_summary`
  (FR-012b "preserve author/approver separation across spec, plan,
  task, and ratification time").

## Acceptance evidence

- Plan-level wrapper conformance is part of US2 acceptance scenarios
  (the spec/plan/tasks triple is governed together).
