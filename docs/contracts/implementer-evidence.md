# Contract: Implementer Evidence Record

Source FRs: FR-001 (machine-readable record contract), FR-027
(failure messages cite contract).
Validator check: `implementer_evidence_schema`
Schema: `schemas/implementer-evidence.schema.yaml`
Template: `templates/implementer-evidence.template.yaml`

## Purpose

An Implementer Evidence Record is the machine-readable form of the
implementer's execution output: what implementation subject was
addressed, which artifacts were authored or updated, the declared
allowed authoring boundary, which mutation classes the executed
change touches, which prohibited surfaces the implementer
affirmatively acknowledged as out of execution scope, which
validation and test evidence the implementer produced, any
deviations from the envelope, what implementer-evidence-only
verdict was issued, and the explicit non-ratification statement.

A reader with only a fresh clone must be able to read this record
and answer:

- which implementation subject was executed
  (`implementation_subject`);
- which artifacts the implementer authored or updated
  (`authored_artifact_refs`);
- which paths formed the allowed authoring boundary
  (`allowed_path_boundary_refs`);
- which ratified implementer identity authored the evidence
  (`implementer_identity_ref`, `implementer_role_category`);
- what execution mode was used (`execution_mode`);
- what was in and out of scope (`implementation_scope`);
- which mutation classes the executed change touches and which
  prohibited surfaces were acknowledged out of scope
  (`mutation_classes_executed`,
  `prohibited_surfaces_acknowledged`);
- which validation and test evidence the implementer produced
  (`validation_evidence_refs`, `test_evidence_refs`);
- what summary, deviations, and open questions the implementer
  surfaced (`implementation_summary`, `deviations`,
  `open_questions`);
- what implementer-evidence-only verdict was issued (`verdict`);
  and
- the explicit non-ratification statement
  (`non_ratification_statement`).

Implementer evidence is **not** review evidence and is **not**
architect evidence. The separate contracts at
[`./review-evidence.md`](./review-evidence.md) (Batch 2D.1) and
[`./architect-evidence.md`](./architect-evidence.md) (Batch 2D.2)
govern those artifact classes. Where this contract and a future
revision of the Batch 2A role/authority decision or the Batch 2B
agent interaction model disagree, the upstream governance
documents are the authority and the schema MUST be revised to
match through the lifecycle.

## Relationship to upstream sources of truth

| Upstream source of truth | Role |
|---|---|
| [`../governance/CODEX_ROLE_AND_AUTHORITY_DECISION.md`](../governance/CODEX_ROLE_AND_AUTHORITY_DECISION.md) | Batch 2A ratified Option C (per-batch architect/implementer authoring assignment) and the §6.3 authority-boundary statement (architect/implementer parity is authoring/execution parity, not ratification/merge/deploy authority). |
| [`../architecture/agent-interaction-model.md`](../architecture/agent-interaction-model.md) | Batch 2B encoded the envelope-bound authority wording for implementer-class envelopes. |
| [`../governance/CODEX_FIRST_CLASS_SCOPE.md`](../governance/CODEX_FIRST_CLASS_SCOPE.md) | Bounded CFC scope, including the standing invariant that any Codex implementer authoring is envelope-bound and Source-ratified per batch. |
| [`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md) | Author/approver separation; implementer authors evidence, implementer does not ratify. |
| [`./identity-record.md`](./identity-record.md) | Implementer identity record contract; the `implementer_identity_ref` field points at a record conforming to this contract. |
| [`./mutation-class-taxonomy.md`](./mutation-class-taxonomy.md) | Mutation class taxonomy; `mutation_classes_executed` entries resolve here. |
| [`./review-evidence.md`](./review-evidence.md) | Sibling Batch 2D.1 review-evidence contract; implementer evidence is a separate artifact class and does not amend review-evidence semantics. |
| [`./architect-evidence.md`](./architect-evidence.md) | Sibling Batch 2D.2 architect-evidence contract; implementer evidence is a separate artifact class and does not amend architect-evidence semantics. |

## Required fields

All required fields MUST be present and non-empty unless a stricter
type rule below applies.

| Field | Type | Rule |
|---|---|---|
| `evidence_id` | string | kebab-case slug matching `^[a-z][a-z0-9-]*$`; stable repo-relative identifier. |
| `implementation_subject` | string | non-empty human-readable statement of the implementation subject. |
| `authored_artifact_refs` | array<string> | non-empty; unique; each item a non-empty repo-relative path. |
| `allowed_path_boundary_refs` | array<string> | non-empty; unique; each item a non-empty repo-relative path. Declares the allowed authoring boundary the envelope authorized; every entry in `authored_artifact_refs` MUST also be inside this boundary. |
| `implementer_identity_ref` | string | non-empty repo-relative path to a ratified implementer identity record. |
| `implementer_role_category` | const | fixed to `implementer`. |
| `execution_mode` | enum | one of `manual_human`, `manual_agent`, `mixed_human_and_agent`. |
| `implementation_scope` | string | non-empty in/out-of-scope statement. |
| `mutation_classes_executed` | array<string> | non-empty; unique; each entry kebab-case slug. |
| `prohibited_surfaces_acknowledged` | array<string> | non-empty; unique; each entry a non-empty surface label. |
| `validation_evidence_refs` | array<string> | each entry non-empty; MAY be empty if the envelope explicitly authorizes implementation with no validator surface to run. |
| `test_evidence_refs` | array<string> | each entry non-empty; MAY be empty if the envelope explicitly authorizes implementation with no test surface to run. |
| `implementation_summary` | string | non-empty free-text summary of executed change. |
| `deviations` | array<object> | structured records; each has `deviation_id`, `summary`, `justification`, `remediation_status`. MAY be empty when execution proceeded without deviation. |
| `open_questions` | array<string> | each entry non-empty; MAY be empty when the implementer has no open questions. |
| `verdict` | enum | one of `implementation_complete`, `implementation_partial`, `scope_boundary_unclear`, `cannot_implement`. |
| `recommended_follow_up` | string | free-text recommendations; MAY be empty. |
| `evidence_timestamp` | string | ISO-8601 timestamp, `commit:<sha>` reference, or `source-controlled:<path>` reference. |
| `non_ratification_statement` | string | non-empty explicit statement that this record is NOT Source ratification. |

`unevaluatedProperties: false` applies at every object level; any
field not listed in the schema is a contract violation.

## Verdict semantics

`verdict` is constrained to implementer-evidence-only outcomes.
These are the only governed verdict values:

| Verdict | Meaning |
|---|---|
| `implementation_complete` | Implementer executed the complete authored boundary within stated scope. Not Source ratification; MUST NOT be treated as authorization to merge, deploy, mutate branch protection, mutate repository settings, delete branches, advance a privileged class, bind a provider/tool/model/host/account or tenant, expand authority, or substitute for review evidence or architect evidence. |
| `implementation_partial` | Implementer executed a partial authored boundary; further authoring is required (a follow-on implementer envelope, a Source clarification, or both). The downstream gate is not yet cleared by this record. |
| `scope_boundary_unclear` | Implementer could not determine whether the implementation subject fits the ratified envelope. The next governed action is a Source clarification, not a verdict override. |
| `cannot_implement` | Implementer is unable to perform the execution (missing artifacts, missing implementer identity record, ratification conflict, authority conflict, boundary contradiction, or other halt condition). Advancement past the implementer gate is blocked until the named condition clears. |

The schema MUST NOT accept any verdict value that implies the
implementer can ratify, approve merge, waive a privileged gate,
modify branch protection, run or modify deploy automation, apply
live repository settings, bind a provider/tool/model/host/account
or tenant, expand authority, or substitute for review evidence or
architect evidence.

## Allowed path boundary

`allowed_path_boundary_refs` is mandatory and non-empty. It MUST
declare the repo-relative paths the envelope authorized the
implementer to touch. The implementer asserts that no tracked path
outside this boundary was modified under the envelope.

Naming a path here does NOT authorize a privileged class on that
path; the privileged-class envelope still requires Source
ratification per Feature 001 FR-008. Boundary expansion is not
performed inside an implementer envelope; an `unresolved` or
`deferred_to_follow_up` deviation under `deviations` signals
boundary ambiguity for Source review.

## Deviations

`deviations` MAY be empty when execution proceeded without
deviation. When present, each entry MUST carry:

| Field | Type | Rule |
|---|---|---|
| `deviation_id` | string | kebab-case slug matching `^[a-z][a-z0-9-]*$`. |
| `summary` | string | non-empty free-text summary of the deviation. |
| `justification` | string | non-empty free-text justification, including why the deviation did not constitute boundary expansion. |
| `remediation_status` | enum | one of `remediated_in_envelope`, `deferred_to_follow_up`, `unresolved`. |

Naming a deviation here does NOT authorize a boundary expansion;
an `unresolved` or `deferred_to_follow_up` deviation is a signal
for Source review and MUST NOT be treated as silent ratification.
Expected-fail behavior of malformed examples and other
documented-expected validator outcomes MAY be recorded as
`remediated_in_envelope` deviations or omitted entirely; either
posture is consistent with the contract.

## Non-ratification statement

`non_ratification_statement` is mandatory. Its absence is itself a
contract violation rejected by the validator with `FR-001`. The
statement MUST restate that this evidence is NOT Source
ratification and does not authorize merge, deploy, branch
deletion, branch protection mutation, live repository-settings
change, provider/tool/model/host/account binding, tenant binding,
or authority expansion. The statement SHOULD additionally restate
that implementer-evidence framing does not substitute for review
evidence or architect evidence under separately Source-ratified
envelopes.

## Evidence timestamp

`evidence_timestamp` MUST be either an ISO-8601 timestamp (e.g.,
`2026-05-17T12:00:00Z`), a `commit:<sha>` reference, or a
`source-controlled:<repo-relative path>` reference. A
machine-local clock value MUST NOT be presented as authoritative;
deployment overlays MAY bind the source-controlled reference to a
particular commit-bound evidence file under the substrate's
storage conventions.

## Forbidden content

An implementer evidence record MUST NOT contain:

- a hard-coded implementer product, model, CLI, SaaS account,
  runner, source-host application, bot slug, or tooling identifier
  as a normative upstream binding (concrete selection is a
  deployment-time overlay decision);
- real emails, tokens, secrets, credentials, source-host
  installation ids, durable actor ids, app slugs, or account
  names;
- machine-local absolute paths, local terminal identifiers, local
  session identifiers, or forensic session-backup paths;
- LIMITLESS-specific identifiers (FR-024, FR-024a, SC-004);
- claims of authority to ratify, approve merge, waive a privileged
  gate, modify branch protection, mutate repository settings, run
  or modify deploy automation, delete or rename branches, alter
  source-host metadata, bind a provider/tool/model/host/account or
  tenant, expand authority, or substitute for review evidence or
  architect evidence.

## Validator behavior

The `implementer_evidence_schema` check discovers candidate
implementer evidence files by file shape (`.yml` / `.yaml`, not
under `schemas/`) and `implementer_role_category == implementer`,
then validates each candidate against
`schemas/implementer-evidence.schema.yaml`. Every failure cites:

- `FR-001` as the violated code;
- the field/path that violated it (JSON Pointer relative to the
  record); and
- this contract document per FR-027.

## Relationship to sibling evidence classes

Batch 2D.3 lifts only the implementer-evidence contract. Sibling
machine-readable schemas are governed by their own separately
Source-ratified privileged `schema`-class envelopes:

- Batch 2D.1 — review-evidence schema (landed; see
  [`./review-evidence.md`](./review-evidence.md)). Implementer
  evidence is a separate artifact class and does NOT amend
  review-evidence semantics, schema, validator, or examples.
- Batch 2D.2 — architect-evidence schema (landed; see
  [`./architect-evidence.md`](./architect-evidence.md)).
  Implementer evidence is a separate artifact class and does NOT
  amend architect-evidence semantics, schema, validator, or
  examples. Implementer-evidence framing does not substitute for
  architect authoring under an architect-class envelope.

This contract MUST NOT be amended by a later batch without going
through the lifecycle.
