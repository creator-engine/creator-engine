# Contract: Definition of Ready

Source FRs: FR-013, FR-013a
Validator check: `definition_of_ready`

## Purpose

The Definition of Ready is the gate between `draft` and `ready` for a
Creator Engine spec wrapper sidecar. A work item MUST NOT be dispatched to
`in_progress` unless it has an explicit scope, acceptance criteria, and
verification declaration.

## Ready-or-later statuses

The gate applies to these statuses:

- `ready`
- `in_progress`
- `verified`
- `ratified`
- `done`

`draft` may be incomplete. Every status after `draft` must satisfy this
contract.

## Required ready fields

For ready-or-later status, the spec sidecar MUST contain non-empty:

- `scope`: markdown string explaining the work boundary.
- `acceptance_criteria`: array of one or more acceptance criteria.
- `verification`: object with:
  - `method`: non-empty string.
  - `evidence_refs`: array of one or more evidence references.

Missing or empty fields are FR-013 violations and must be reported with the
specific field path and this contract path.
