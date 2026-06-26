# Contract: Review Evidence Record

Source FRs: FR-001 (machine-readable record contract), FR-027
(failure messages cite contract).
Validator check: `review_evidence_schema`
Schema: `schemas/review-evidence.schema.yaml`
Template: `templates/review-evidence.template.yaml`
Upstream prose template contract:
[`../delivery/REVIEW_EVIDENCE_TEMPLATE.md`](../delivery/REVIEW_EVIDENCE_TEMPLATE.md)

## Purpose

A Review Evidence Record is the machine-readable form of the
existing prose review-evidence contract at
[`../delivery/REVIEW_EVIDENCE_TEMPLATE.md`](../delivery/REVIEW_EVIDENCE_TEMPLATE.md).
A reviewer with only a fresh clone must be able to read this
record and answer:

- which artifacts and diff/commit range were under review
  (`reviewed_artifact_refs`, `reviewed_diff_or_commit_ref`);
- which ratified reviewer identity authored the evidence
  (`reviewer_identity_ref`, `reviewer_role_category`);
- which model-level independence attestation was recorded
  (`reviewer_model`, `authorship_obfuscated`,
  `adversarial_prompt`);
- what review mode was used (`review_mode`);
- what was in and out of scope (`review_scope`);
- which mutation classes were touched and which prohibited
  surfaces were affirmatively checked
  (`mutation_classes_under_review`, `prohibited_surfaces_checked`);
- which validation evidence and findings were observed
  (`validation_evidence_refs`, `findings`, `blocking_findings`,
  `non_blocking_findings`);
- what evidence-only verdict was issued (`verdict`); and
- the explicit non-ratification statement
  (`non_ratification_statement`).

Where this contract and the upstream prose template at
[`../delivery/REVIEW_EVIDENCE_TEMPLATE.md`](../delivery/REVIEW_EVIDENCE_TEMPLATE.md)
disagree, the prose template is the authority for human review and
the schema MUST be revised to match through the lifecycle.

## Relationship to upstream sources of truth

| Upstream source of truth | Role |
|---|---|
| [`../delivery/REVIEW_EVIDENCE_TEMPLATE.md`](../delivery/REVIEW_EVIDENCE_TEMPLATE.md) | Prose template contract this schema lifts. Field semantics, forbidden content, and storage-policy boundary live there. |
| [`../delivery/REVIEWER_IDENTITY_REQUIREMENTS.md`](../delivery/REVIEWER_IDENTITY_REQUIREMENTS.md) | Reviewer identity pattern that authorizes who may author review evidence. |
| [`../delivery/REVIEW_GATE.md`](../delivery/REVIEW_GATE.md) | Review-gate definition that names when review evidence is required and how it is evaluated. |
| [`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md) | Author/approver separation; reviewer writes review evidence, reviewer does not ratify. |
| [`./identity-record.md`](./identity-record.md) | Reviewer identity record contract; the `reviewer_identity_ref` field points at a record conforming to this contract. |
| [`./mutation-class-taxonomy.md`](./mutation-class-taxonomy.md) | Mutation class taxonomy; `mutation_classes_under_review` entries resolve here. |

## Required fields

All required fields MUST be present and non-empty unless a stricter
type rule below applies.

| Field | Type | Rule |
|---|---|---|
| `evidence_id` | string | kebab-case slug matching `^[a-z][a-z0-9-]*$`; stable repo-relative identifier. |
| `reviewed_artifact_refs` | array<string> | non-empty; unique; each item a non-empty repo-relative path. |
| `reviewed_diff_or_commit_ref` | string | non-empty diff range or commit-ish reference. |
| `reviewer_identity_ref` | string | non-empty repo-relative path to a ratified reviewer identity record. |
| `reviewer_role_category` | const | fixed to `reviewer`. |
| `reviewer_model` | string | non-empty reviewer-supplied model identifier used for independence checks; evidence attestation only, not a normative upstream product/model binding. |
| `authorship_obfuscated` | boolean | true when the reviewer received an authorship-obfuscated prompt or packet for this review. |
| `adversarial_prompt` | boolean | true when the review prompt explicitly asked for adversarial blocking-finding discovery rather than agreement or approval. |
| `review_mode` | enum | one of `manual_human`, `manual_agent`, `mixed_human_and_agent`. |
| `review_scope` | string | non-empty in/out-of-scope statement. |
| `mutation_classes_under_review` | array<string> | non-empty; unique; each entry kebab-case slug. |
| `prohibited_surfaces_checked` | array<string> | non-empty; unique; each entry a non-empty surface label. |
| `validation_evidence_refs` | array<string> | each entry non-empty; MAY be empty if the reviewer consulted no validation refs. |
| `findings` | string | non-empty free-text observations. |
| `blocking_findings` | array<object> | structured records; each has `artifact_ref`, `rule_violated`, `recommended_remediation`. |
| `non_blocking_findings` | array<object> | structured records; each has `artifact_ref`, `observation`, `advisory_follow_up`. |
| `verdict` | enum | one of `no_blocking_findings`, `blocking_findings_present`, `scope_boundary_unclear`, `cannot_review`. |
| `recommended_follow_up` | string | free-text recommendations; MAY be empty. |
| `evidence_timestamp` | string | ISO-8601 timestamp, `commit:<sha>` reference, or `source-controlled:<path>` reference. |
| `non_ratification_statement` | string | non-empty explicit statement that this record is NOT Source ratification. |

`unevaluatedProperties: false` applies at every object level; any
field not listed in the schema is a contract violation.

## Verdict semantics

`verdict` is constrained to evidence-only outcomes. These are the
only governed verdict values:

| Verdict | Meaning |
|---|---|
| `no_blocking_findings` | Review completed within stated scope; no blocking findings observed. Advisory non-blocking findings MAY be present. Not Source ratification; MUST NOT be treated as authorization to merge, deploy, mutate branch protection, mutate repository settings, delete branches, or advance a privileged class. |
| `blocking_findings_present` | Reviewer observed one or more blocking findings. The review gate halts the batch per [`../delivery/REVIEW_GATE.md`](../delivery/REVIEW_GATE.md); remediation, scrap/redo, or Source-directed disposition follows. |
| `scope_boundary_unclear` | Reviewer could not determine whether the change fits the ratified envelope. The next governed action is a Source clarification, not a verdict override. |
| `cannot_review` | Reviewer is unable to perform the review (missing artifacts, missing reviewer identity record, ratification conflict, authority conflict, or other halt condition). Advancement past the review gate is blocked until the named condition clears. |

The schema MUST NOT accept any verdict value that implies the
reviewer can ratify, approve merge, waive a privileged gate, modify
branch protection, run or modify deploy automation, or apply live
repository settings.

## Non-ratification statement

`non_ratification_statement` is mandatory. Its absence is itself a
`blocking_findings` condition under
[`../delivery/REVIEW_GATE.md`](../delivery/REVIEW_GATE.md) §g and is
rejected by the validator with `FR-001`. The statement MUST
restate that this evidence is NOT Source ratification and does not
authorize merge, deploy, branch deletion, branch protection
mutation, or live repository-settings change.

## Evidence timestamp

`evidence_timestamp` MUST be either an ISO-8601 timestamp (e.g.,
`2026-05-17T12:00:00Z`), a `commit:<sha>` reference, or a
`source-controlled:<repo-relative path>` reference. A machine-local
clock value MUST NOT be presented as authoritative; deployment
overlays MAY bind the source-controlled reference to a particular
commit-bound evidence file under the substrate's storage
conventions.

## Forbidden content

Per [`../delivery/REVIEW_EVIDENCE_TEMPLATE.md`](../delivery/REVIEW_EVIDENCE_TEMPLATE.md)
§f, a review evidence record MUST NOT contain:

- a hard-coded reviewer product, model, CLI, SaaS account, runner,
  source-host application, bot slug, or QA harness as a normative
  upstream binding (concrete selection is a deployment-time overlay
  decision). `reviewer_model` is permitted only as a reviewer-supplied
  evidence attestation for mode-aware independence checks;
- real emails, tokens, secrets, credentials, source-host
  installation ids, durable actor ids, app slugs, or account names;
- machine-local absolute paths, local terminal identifiers, local
  session identifiers, or forensic session-backup paths;
- LIMITLESS-specific identifiers (FR-024, FR-024a, SC-004);
- claims of authority to ratify, approve merge, waive a privileged
  gate, modify branch protection, mutate repository settings, run
  or modify deploy automation, delete or rename branches, or alter
  source-host metadata.

## Validator behavior

The `review_evidence_schema` check discovers candidate review
evidence files by file shape (`.yml` / `.yaml`, not under
`schemas/`) and `reviewer_role_category == reviewer`, then
validates each candidate against
`schemas/review-evidence.schema.yaml`. Every failure cites:

- `FR-001` as the violated code;
- the field/path that violated it (JSON Pointer relative to the
  record); and
- this contract document per FR-027.

## Downstream batches

Batch 2D.1 lifts only the review-evidence contract. Sibling
machine-readable schemas remain explicitly downstream and require
their own separately Source-ratified privileged `schema`-class
envelopes:

- Batch 2D.2 — architect-evidence schema (not authored here).
- Batch 2D.3 — implementer-evidence schema (not authored here).

This contract MUST NOT be amended by Batch 2D.2 or Batch 2D.3
without going through the lifecycle.
