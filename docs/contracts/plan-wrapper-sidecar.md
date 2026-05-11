# Contract: Plan Wrapper Sidecar

Source FRs: FR-012a, FR-012b
Canonical filename: `plan.creator-engine.yml`
Schema: `schemas/plan-wrapper-sidecar.schema.yaml`
Validator check: `sidecar_conformance`

## Purpose

A Plan Wrapper Sidecar is the Creator Engine governance wrapper for a
vanilla Spec Kit `plan.md`. It records the plan-level mutation-class
summary, permitted action summary, verification plan, ratification flag,
and identity policy reference without modifying the Markdown plan.

## Sidecar discovery rule (FR-012a)

For any governed Spec Kit plan file, the sidecar is discovered by directory
adjacency:

- Spec Kit file: `plan.md`
- Creator Engine sidecar: `plan.creator-engine.yml`

The sidecar MUST be in the same directory as `plan.md`.

## Required fields

| Field | Type | FR | Rule |
|---|---|---|---|
| `spec_ref` | string | FR-012b | repo-relative reference to the governing spec sidecar |
| `plan_mutation_class_summary` | array<string> | FR-012b | non-empty list of mutation classes touched by the plan |
| `plan_permitted_actions_summary` | array<string> | FR-012b | non-empty list of actions anticipated by the plan |
| `verification_plan` | object | FR-012b | contains `method` and `evidence_refs` |
| `ratification_required` | boolean | FR-012b | mirrors the governing spec expectation |
| `identity_policy_ref` | string | FR-012b | repo-relative reference to the identity record governing the plan |

`sidecar_conformance` validates the field shape. Later mutation-class and
ratification checks validate cross-artifact semantics.
