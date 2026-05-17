# Contract: Architect Evidence Record

Source FRs: FR-001 (machine-readable record contract), FR-027
(failure messages cite contract).
Validator check: `architect_evidence_schema`
Schema: `schemas/architect-evidence.schema.yaml`
Template: `templates/architect-evidence.template.yaml`

## Purpose

An Architect Evidence Record is the machine-readable form of the
architect's authoring output: what design subject the architect
addressed, which artifacts they authored or propose to author,
which mutation classes the proposed change would touch, which
prohibited surfaces the architect affirmatively acknowledged as
out of authoring scope, what decision options and recommendations
the architect surfaced for Source, and the explicit
non-ratification statement.

A reader with only a fresh clone must be able to read this record
and answer:

- which design subject was addressed (`design_subject`);
- which artifacts the architect authored or proposes to author
  (`authored_artifact_refs`);
- which ratified architect identity authored the evidence
  (`architect_identity_ref`, `architect_role_category`);
- what authoring mode was used (`authoring_mode`);
- what was in and out of scope (`design_scope`);
- which mutation classes the proposed change would touch and
  which prohibited surfaces were acknowledged out of scope
  (`mutation_classes_proposed`,
  `prohibited_surfaces_acknowledged`);
- which supporting evidence was consulted
  (`supporting_evidence_refs`);
- what recommendations, decision options, and open questions the
  architect surfaced (`recommendations`, `decision_options`,
  `open_questions`);
- what architect-evidence-only verdict was issued (`verdict`);
  and
- the explicit non-ratification statement
  (`non_ratification_statement`).

Architect evidence is **not** review evidence and is **not**
implementer evidence. The separate contracts at
[`./review-evidence.md`](./review-evidence.md) (Batch 2D.1) and
the future Batch 2D.3 implementer-evidence contract govern those
artifact classes. Where this contract and a future revision of the
Batch 2A role/authority decision or the Batch 2B agent interaction
model disagree, the upstream governance documents are the
authority and the schema MUST be revised to match through the
lifecycle.

## Relationship to upstream sources of truth

| Upstream source of truth | Role |
|---|---|
| [`../governance/CODEX_ROLE_AND_AUTHORITY_DECISION.md`](../governance/CODEX_ROLE_AND_AUTHORITY_DECISION.md) | Batch 2A ratified Option C (per-batch architect/implementer authoring assignment) and the §6.3 authority-boundary statement (architect parity is authoring parity, not ratification/merge/deploy authority). |
| [`../architecture/agent-interaction-model.md`](../architecture/agent-interaction-model.md) | Batch 2B encoded the envelope-bound authority wording for architect-class envelopes. |
| [`../governance/CODEX_FIRST_CLASS_SCOPE.md`](../governance/CODEX_FIRST_CLASS_SCOPE.md) | Bounded CFC scope, including the standing invariant that Codex-as-architect retains authoring parity only. |
| [`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md) | Author/approver separation; architect authors evidence, architect does not ratify. |
| [`./identity-record.md`](./identity-record.md) | Architect identity record contract; the `architect_identity_ref` field points at a record conforming to this contract. |
| [`./mutation-class-taxonomy.md`](./mutation-class-taxonomy.md) | Mutation class taxonomy; `mutation_classes_proposed` entries resolve here. |
| [`./review-evidence.md`](./review-evidence.md) | Sibling Batch 2D.1 review-evidence contract; architect evidence is a separate artifact class and does not amend review-evidence semantics. |

## Required fields

All required fields MUST be present and non-empty unless a stricter
type rule below applies.

| Field | Type | Rule |
|---|---|---|
| `evidence_id` | string | kebab-case slug matching `^[a-z][a-z0-9-]*$`; stable repo-relative identifier. |
| `design_subject` | string | non-empty human-readable statement of the design subject. |
| `authored_artifact_refs` | array<string> | non-empty; unique; each item a non-empty repo-relative path. |
| `architect_identity_ref` | string | non-empty repo-relative path to a ratified architect identity record. |
| `architect_role_category` | const | fixed to `architect`. |
| `authoring_mode` | enum | one of `manual_human`, `manual_agent`, `mixed_human_and_agent`. |
| `design_scope` | string | non-empty in/out-of-scope statement. |
| `mutation_classes_proposed` | array<string> | non-empty; unique; each entry kebab-case slug. |
| `prohibited_surfaces_acknowledged` | array<string> | non-empty; unique; each entry a non-empty surface label. |
| `supporting_evidence_refs` | array<string> | each entry non-empty; MAY be empty if the architect consulted no additional supporting evidence. |
| `recommendations` | string | non-empty free-text recommendations and decision context. |
| `decision_options` | array<object> | structured records; each has `option_id`, `summary`, `tradeoffs`, `recommended_default`. MAY be empty when the recommendation is unitary. |
| `open_questions` | array<string> | each entry non-empty; MAY be empty when the architect has no open questions. |
| `verdict` | enum | one of `recommendation_complete`, `recommendation_partial`, `scope_boundary_unclear`, `cannot_author`. |
| `recommended_follow_up` | string | free-text recommendations; MAY be empty. |
| `evidence_timestamp` | string | ISO-8601 timestamp, `commit:<sha>` reference, or `source-controlled:<path>` reference. |
| `non_ratification_statement` | string | non-empty explicit statement that this record is NOT Source ratification. |

`unevaluatedProperties: false` applies at every object level; any
field not listed in the schema is a contract violation.

## Verdict semantics

`verdict` is constrained to architect-evidence-only outcomes.
These are the only governed verdict values:

| Verdict | Meaning |
|---|---|
| `recommendation_complete` | Architect produced a complete recommendation within stated scope. Not Source ratification; MUST NOT be treated as authorization to merge, deploy, mutate branch protection, mutate repository settings, delete branches, advance a privileged class, or substitute for implementer authoring under an implementer-class envelope. |
| `recommendation_partial` | Architect produced a partial recommendation; further authoring is required (a follow-on architect envelope, a Source clarification, or both). The downstream gate is not yet cleared by this record. |
| `scope_boundary_unclear` | Architect could not determine whether the design subject fits the ratified envelope. The next governed action is a Source clarification, not a verdict override. |
| `cannot_author` | Architect is unable to perform the authoring (missing artifacts, missing architect identity record, ratification conflict, authority conflict, or other halt condition). Advancement past the architect gate is blocked until the named condition clears. |

The schema MUST NOT accept any verdict value that implies the
architect can ratify, approve merge, waive a privileged gate,
modify branch protection, run or modify deploy automation, apply
live repository settings, or substitute for implementer authoring
under an implementer-class envelope.

## Non-ratification statement

`non_ratification_statement` is mandatory. Its absence is itself a
contract violation rejected by the validator with `FR-001`. The
statement MUST restate that this evidence is NOT Source
ratification and does not authorize merge, deploy, branch
deletion, branch protection mutation, or live repository-settings
change. The statement SHOULD additionally restate that
architect-evidence framing does not substitute for implementer
authoring under a separately Source-ratified implementer envelope.

## Evidence timestamp

`evidence_timestamp` MUST be either an ISO-8601 timestamp (e.g.,
`2026-05-17T12:00:00Z`), a `commit:<sha>` reference, or a
`source-controlled:<repo-relative path>` reference. A
machine-local clock value MUST NOT be presented as authoritative;
deployment overlays MAY bind the source-controlled reference to a
particular commit-bound evidence file under the substrate's
storage conventions.

## Forbidden content

An architect evidence record MUST NOT contain:

- a hard-coded architect product, model, CLI, SaaS account,
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
  source-host metadata, or substitute for implementer authoring
  under an implementer-class envelope.

## Validator behavior

The `architect_evidence_schema` check discovers candidate
architect evidence files by file shape (`.yml` / `.yaml`, not
under `schemas/`) and `architect_role_category == architect`, then
validates each candidate against
`schemas/architect-evidence.schema.yaml`. Every failure cites:

- `FR-001` as the violated code;
- the field/path that violated it (JSON Pointer relative to the
  record); and
- this contract document per FR-027.

## Relationship to sibling evidence classes

Batch 2D.2 lifts only the architect-evidence contract. Sibling
machine-readable schemas remain explicitly downstream and require
their own separately Source-ratified privileged `schema`-class
envelopes:

- Batch 2D.1 — review-evidence schema (landed; see
  [`./review-evidence.md`](./review-evidence.md)). Architect
  evidence is a separate artifact class and does NOT amend
  review-evidence semantics, schema, validator, or examples.
- Batch 2D.3 — implementer-evidence schema (not authored here).
  Implementer authoring under an implementer-class envelope is a
  separate artifact class. Architect-evidence framing does not
  substitute for implementer evidence and does not authorize
  implementer-class mutations.

This contract MUST NOT be amended by Batch 2D.3 or any later
batch without going through the lifecycle.
