# Contract: Tasks Wrapper Sidecar

Source FRs: FR-007, FR-012a, FR-012b
Canonical filename: `tasks.creator-engine.yml`
Schema: `schemas/tasks-wrapper-sidecar.schema.yaml`
Validator check: `sidecar_conformance`

## Purpose

A Tasks Wrapper Sidecar is the Creator Engine governance wrapper for a
vanilla Spec Kit `tasks.md`. It keeps Spec Kit tasks byte-compatible while
storing per-task mutation class, permitted actions, verification evidence,
and author/approver linkage in adjacent YAML.

## Sidecar discovery rule (FR-012a)

For any governed Spec Kit tasks file, the sidecar is discovered by
directory adjacency:

- Spec Kit file: `tasks.md`
- Creator Engine sidecar: `tasks.creator-engine.yml`

The sidecar MUST be in the same directory as `tasks.md`.

## Required top-level fields

| Field | Type | FR | Rule |
|---|---|---|---|
| `spec_ref` | string | FR-012b | repo-relative reference to the governing spec sidecar |
| `tasks` | array<TaskEntry> | FR-012b | non-empty array |

## TaskEntry fields

| Field | Type | FR | Rule |
|---|---|---|---|
| `id` | string | FR-012b | unique within this sidecar |
| `title` | string | FR-012b | non-empty task title |
| `mutation_class` | string | FR-012b | declared mutation class name |
| `permitted_actions` | array<string> | FR-012b | non-empty actions for the task |
| `verification_evidence_ref` | string | FR-012b | repo-relative path or anchor naming evidence |
| `author_actor_id` | string | FR-007/FR-012b | actor authoring the task mutation |
| `approver_actor_id` | string, optional | FR-007 | when present, MUST NOT equal `author_actor_id` |
| `ratification_or_approval_ref` | string, optional | FR-012b | approval or ratification evidence reference when known |

The schema validates shape and uniqueness. The sidecar conformance check
also enforces the author/approver inequality when both actors are present.
