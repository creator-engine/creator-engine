# Contract: Authority Matrix

Source FRs: FR-015, FR-007, FR-008, FR-017, FR-018
Validator check: `authority_matrix` (deferred to sub-batch A2)
Schema: `schemas/authority-matrix.schema.yaml`
Baseline data: `docs/contracts/authority-matrix.yml`

## Purpose

The authority matrix names, for each generic role category, the
allowed instruction sources, the mutation classes a role may author
work in, the role required to ratify that work, the communication
surfaces the role may operate on, and the audit artifacts the role
must produce.

The substrate ships exactly seven baseline rows — one per
`role_category` enum value (Source-approved Escalation 2 Option (a),
2026-05-10). Across the seven rows, every baseline mutation class
MUST appear in at least one row's `allowed_mutation_classes`. Tenant-
specific role names, surfaces, or audit artifacts belong in
`tenants/<name>/authority-matrix-overlay.yml`, never in this file or
in `docs/contracts/authority-matrix.yml`.

## Role categories

The seven baseline `role_category` enum values, mirrored from the
identity-record schema:

| `role_category` | Description |
|---|---|
| `source` | Project owner/operator with authority to approve governance direction and ratify privileged mutations. |
| `ratifier` | Human or named role authorized by Source to accept a mutation after reviewing its evidence. |
| `reviewer` | Provides review/advisory text on artifacts under review; does not author the mutation under review. |
| `architect` | Designs the spec/plan/contract for a feature; authors generic contract documents and schemas. |
| `implementer` | Authors the code, schema, or docs that fulfills an approved spec/plan/tasks triple. |
| `verifier` | Authors verification artifacts (tests, validators, verification scripts). |
| `observer` | Writes observation artifacts (notes, handoffs); least-privilege role. |

## Per-row shape

Each row in `authority-matrix.yml` and any tenant overlay row MUST
have:

| Field | Type | FR | Rule |
|---|---|---|---|
| `role_category` | enum | FR-015 | one of the seven values above; baseline file requires exactly one row per value |
| `tenant_role_name` | string (optional) | FR-015 | overlay-only; absent in the substrate baseline; tenants may use this to alias a baseline `role_category` to a tenant-specific name |
| `allowed_instruction_sources` | array<string> | FR-015 | non-empty; the kinds of artifact or directive that this role may take work from (e.g., `spec`, `plan`, `tasks`, `source_directive`, `ratification_record`) |
| `allowed_mutation_classes` | array<string> | FR-015 | non-empty; in the baseline file, items MUST be drawn from the nine baseline class names |
| `required_ratifier_role` | enum | FR-015/FR-008 | one of the seven `role_category` values; for FR-008 privileged-class rows, MUST be `source` or `ratifier` (human-eligible) |
| `allowed_communication_surfaces` | array<string> | FR-015 | non-empty; named surfaces on which this role may operate (e.g., `repo_pr`, `repo_review`, `repo_commit_message`, `repo_issue`, `repo_attestation_record`, `repo_ratification_record`) |
| `required_audit_artifacts` | array<string> | FR-015 | non-empty; artifacts this role MUST produce or be named in (e.g., `attestation_record`, `ratification_record`) |

## Coverage rule (FR-015)

Across the seven baseline rows, every baseline mutation class
(`docs`, `code`, `schema`, `deploy`, `governance`, `identity`,
`security`, `attestation`, `redaction`) MUST appear in at least one
row's `allowed_mutation_classes`. Coverage is verified by the
authority-matrix check in sub-batch A2; the schema cannot enforce
cross-row coverage and so does not.

## FR-008 privileged-class wiring (Reading A strict)

Source approved Reading A on 2026-05-10. For any row whose
`allowed_mutation_classes` contains a privileged baseline class
(`deploy`, `governance`, `identity`, `security`, `attestation`,
`redaction`), `required_ratifier_role` MUST resolve to a human-
eligible role. In v0.1 the human-eligible roles are `source` and
`ratifier`; the schema enforces this via an `if/then` constraint.

For non-privileged rows (those whose `allowed_mutation_classes`
contains only `docs`, `code`, `schema` from the baseline set), any
of the seven role categories is acceptable as
`required_ratifier_role`.

This rule does not name a specific human user. Tenants name the
human ratifier (or roster of ratifiers) in their identity record's
`human_ratifier_roles` field and in their authority-matrix overlay's
`tenant_role_name` aliases; the baseline matrix only constrains the
role-category shape.

## Ratification flow (forward cross-reference)

The full ratification flow — including which surfaces count as
*valid* ratification surfaces per mutation class — is defined in
`docs/contracts/ratification-flow.md` (sub-batch B). Three policy
claims are anchored here so reviewers can locate them in the matrix:

1. **Surface validity is policy-driven.** A surface that appears in
   a row's `allowed_communication_surfaces` is permitted to *carry*
   ratification artifacts; whether a given surface counts as a
   *valid ratification surface* for a given mutation class is
   governed by the ratification flow document and tenant
   `tenants/<name>/ratification-flow.yml` overlay.

2. **Agent-authored review text is not ratification for FR-008
   privileged classes.** Per FR-017, agent-authored review text MAY
   be recorded as review evidence on non-privileged classes only if
   the matrix authorises that role instance for that evidence
   role; for privileged classes, agent-authored text is never
   ratification regardless of surface.

3. **A "go ahead" message is not merge authorisation by itself.**
   Per FR-018, a "go ahead" or equivalent message on a surface that
   the ratification flow has not designated as a valid ratification
   surface for the relevant mutation class does not authorise
   merge, deploy, publish, or any other reserved-restricted action.

## Author definition (forward-compatibility note)

The authority matrix does NOT redefine "author" for the FR-007
author/approver separation rule. The candidate v0.1 rule (to be
finalised in sub-batch B / `docs/contracts/ratification-flow.md`) is:
"the author identity for a mutation, for the purposes of FR-007, is
the union of every `author_actor_id` value in the corresponding
`tasks.creator-engine.yml`'s TaskEntries; a ratifier MUST NOT equal
any member of that set." Authority-matrix prose intentionally does
not foreclose this rule.

## Tenant overlay rule

Tenant overlays live in `tenants/<name>/authority-matrix-overlay.yml`
and validate against a separate, looser schema (not part of A1).
Overlays:

- alias a baseline `role_category` to a tenant-specific
  `tenant_role_name` (e.g. a tenant title or named ratifier role);
- MAY add tenant-specific surfaces or audit artifacts;
- MUST NOT redefine the baseline rule that FR-008 privileged-class
  rows require a human-eligible `required_ratifier_role`;
- MUST NOT introduce tenant-specific identifiers into the substrate's
  generic-contract paths (FR-024).

Tenant-specific overlay material lives only at
`tenants/<name>/authority-matrix-overlay.yml` for the corresponding
tenant; the dogfood tenant fixture is no exception.

## Validator behavior

The `authority_matrix` check (sub-batch A2) cites this contract on
every failure per FR-027:

- row count != 7 in the baseline file: `FR-015: docs/contracts/authority-matrix.yml: baseline matrix MUST contain exactly 7 rows (consult docs/contracts/authority-matrix.md)`
- duplicate `role_category` across rows: `FR-015: <path>: role_category <value> appears in more than one baseline row (consult docs/contracts/authority-matrix.md)`
- baseline mutation class not covered by any row: `FR-015: docs/contracts/authority-matrix.yml: baseline class <name> is not present in any row's allowed_mutation_classes (consult docs/contracts/authority-matrix.md)`
- privileged-class row with non-human-eligible ratifier: `FR-008: <path>: row for <role_category> includes privileged class <name> but required_ratifier_role <value> is not human-eligible (consult docs/contracts/authority-matrix.md)`
- tenant-specific identifier under generic-contract paths: `FR-024: <path>: tenant-specific identifier <token> in generic-contract path (consult docs/contracts/authority-matrix.md)`
