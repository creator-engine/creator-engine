# Reviewer Identity Requirements (Generic Pattern)

**Status**: Slice D authored draft. This document defines a generic
reviewer identity record **pattern**, not a real reviewer identity.
Upstream Creator Engine does not instantiate a real tenant or
deployment reviewer identity under Slice D. Concrete bindings to a
tool, model, host application, durable actor, runner, or
source-host installation are **deployment-time overlay decisions**
and are out of scope for this upstream document. Instantiation of a
governed reviewer identity record (including its Source ratification)
is downstream Feature 004 work and requires its own per-batch
privileged envelope.

Part of the **minimum repo-native delivery control plane** and
**not a Jira clone**. Layered onto, and subordinate to, the Feature
001 substrate
([`../contracts/identity-record.md`](../contracts/identity-record.md),
[`../../templates/identity-record.template.yaml`](../../templates/identity-record.template.yaml),
[`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md))
and the Feature 002 operating model.

## a. Purpose

A reviewer identity record makes a single fact answerable from a fresh
clone:

> Who is authorized to author independent review evidence for a given
> mutation, under whose ratified authority, and within what scope?

The Slice D scope is to author the **pattern** that any future
governed reviewer identity record MUST satisfy. The pattern is
intentionally project-, tenant-, runtime-, model-, and harness-
agnostic. It does not select a reviewer tool, model, CLI, source-host
installation, application slug, durable actor, account, or runner.

## b. Source-of-truth relationship

The reviewer identity pattern is **derived from**, and subordinate
to, the Feature 001 identity-record contract. It does not redefine
that contract.

| Upstream source of truth | Role |
|---|---|
| [`../contracts/identity-record.md`](../contracts/identity-record.md) | Canonical identity-record field schema and validation expectations. |
| [`../../templates/identity-record.template.yaml`](../../templates/identity-record.template.yaml) | Generic identity-record template shape. Existing example values are illustrative, not normative. |
| [`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md) §b–§e | Reviewer authors review evidence; reviewer does not ratify. Identity is privileged. Author/approver separation. Authority-conflict halt/escalation path. |
| [`./DEFINITION_OF_READY.md`](./DEFINITION_OF_READY.md) §b, §c | Eleven Ready criteria; the privileged-class rule; author/approver separation. |
| [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §b.4, §b.5 | Independent review evidence where applicable; review is not ratification; privileged classes require Source ratification. |
| Feature 001 FR-008 | Privileged-class enumeration. `identity` is privileged. |
| Feature 001 FR-007 | Author/approver separation. |
| Feature 002 FR-018 | Authority-conflict halt/escalation path. |
| [`../../specs/sprint-0-minimum-viable-delivery-system/README.md`](../../specs/sprint-0-minimum-viable-delivery-system/README.md) §4 exit gates #7 and #10 | Sprint 0 acceptance gates for governed roles and review evidence format. |

Where this document and any upstream source disagree, the upstream
source of truth controls until Source ratifies a correction.

## c. Invariants

The following invariants apply to every governed reviewer identity
record produced under this pattern, regardless of deployment overlay:

1. Upstream Creator Engine **does not instantiate** a real tenant or
   deployment reviewer identity under Slice D. Instantiation is
   downstream Feature 004 work under its own Source-ratified
   privileged envelope.
2. Concrete bindings — reviewer tool, model, CLI, host application,
   durable actor, source-host installation, account, runner, or
   harness — are **deployment-time overlay decisions** and MUST NOT
   appear as upstream constants in this document or in any other
   Slice D artifact.
3. A reviewer identity MAY author **review evidence only** within the
   mutation classes and repositories named by its ratified identity
   record. It MUST NOT author other mutations.
4. Reviewer evidence is **advisory/governance evidence**, not Source
   ratification. A reviewer verdict, CI green check, agent commentary,
   or external tracker signal MUST NOT be treated as Source
   ratification of the underlying change.
5. **Default rule**: the reviewer identity MUST NOT author the
   mutation it reviews. The default is independent review. A narrow
   exception (e.g., self-review of trivial mechanical edits) is
   permitted **only if Source separately ratifies that exception** as
   part of the relevant envelope.
6. **Privileged classes remain Source-ratified** (Feature 001 FR-008).
   A reviewer verdict — including "no blocking findings" — never
   substitutes for Source ratification of `deploy`, `governance`,
   `identity`, `security`, `attestation`, or `redaction` mutations.
7. **Author/approver separation** applies (Feature 001 FR-007). The
   actor who authors a mutation MUST NOT be its ratifier. The actor
   who authors review evidence on a mutation MUST NOT also ratify
   that mutation.
8. Review evidence MUST NOT claim authority to approve merge, modify
   branch protection, mutate repository settings, run or modify
   deploy automation, delete or rename branches, or alter
   source-host metadata.

## d. Required record fields (generic pattern)

Every governed reviewer identity record MUST populate the following
fields or their equivalents in the Feature 001 identity-record
contract. Field-level rules in
[`../contracts/identity-record.md`](../contracts/identity-record.md)
remain authoritative.

| Field | Pattern rule | Upstream binding constraint |
|---|---|---|
| `tenant_id` | Deployment overlay owner; kebab-case per Feature 001 rule. | Placeholder/overlay value only; no real tenant identifier upstream. |
| `source_host` | Enum permitted by Feature 001 (e.g., `github`). | Placeholder/overlay value only. |
| `source_host_installation_id` | Source-host installation binding. | **Placeholder only.** No real installation id upstream. |
| `agent_app_slug` | Application or bot binding. | **Placeholder only.** No real app slug upstream. |
| `agent_actor_id` | Durable actor binding. | **Placeholder only.** No real actor id upstream. |
| `runtime_tool` | Runtime tool name selected at deployment-time. | **Deployment-time value, not an upstream constant.** No specific reviewer product, model, or CLI named upstream. |
| `role_category` | `role_category: reviewer`. | Fixed by this pattern. |
| `authority_context.description` | Human-readable rationale for reviewer authority. | Must describe scope as review-evidence-authoring only; MUST NOT claim ratification authority. |
| `authority_context.governing_spec_refs` | Repo-relative paths to specs that authorize the reviewer. | At minimum cites Feature 001 / Feature 002 substrate and Slice D documents under this directory. |
| `authority_context.ratifier_authority_refs` | Repo-relative paths to artifacts declaring ratification expectations. | Must point at Source-ratified authority artifacts; reviewer evidence MUST NOT appear here as a ratification source. |
| `human_ratifier_roles` | Non-empty array. | MUST include `source` for any privileged-class mutation the reviewer's evidence informs. |
| `mutation_classes` | Mutation classes the reviewer identity is authorized to author. | Limited to evidence-authoring classes (e.g., `governance` or `docs` for the evidence artifact itself). MUST NOT include privileged classes belonging to the change under review (`deploy`, `identity`, `security`, `attestation`, `redaction`, or `governance` mutations beyond the reviewer's own evidence files). |
| `allowed_repositories` | Repositories the reviewer identity may write to. | **Deployment-time values or placeholders.** No real repository identifiers introduced as upstream constants by this Slice D document. |
| `signing_policy` | Signing booleans/method per Feature 001 signing policy contract. | Pattern-level reference; concrete keys/methods are deployment-time. |
| `attestation_storage_path` | Repo-relative directory path. | Pattern-level placeholder; concrete path is deployment-time. |
| `ratification_storage_path` | Repo-relative directory path. | Pattern-level placeholder; concrete path is deployment-time. |
| `redaction_storage_path` | Repo-relative directory path. | Pattern-level placeholder; concrete path is deployment-time. |
| `platform_identity_ref` *(optional)* | Reference to a separate platform-identity record if present. | Optional; placeholder only upstream. |

The record's `mutation_classes` array is the operative authority
boundary for the reviewer. A reviewer identity is not implicitly
authorized to act outside that array.

## e. Forbidden content for this pattern

A reviewer identity requirements document, and any Slice D artifact
that references it, MUST NOT contain:

- a hard-coded reviewer product, model, CLI, SaaS account, runner,
  source-host application, bot slug, or QA harness as a normative
  upstream binding;
- a real tenant or customer identifier beyond a generic placeholder;
- a real source-host installation id, durable actor id, application
  slug, email address, token, secret, credential, or account name;
- a machine-local absolute path, local terminal identifier, local
  session identifier, or forensic session-backup path;
- any claim that a reviewer identity is authorized to ratify a
  mutation, approve merge, waive a privileged gate, modify branch
  protection, mutate repository settings, run or modify deploy
  automation, delete or rename branches, or alter source-host
  metadata.

Existing named examples in upstream anchors (templates, contracts,
prior specs) remain **examples only**. They MUST NOT be promoted into
upstream constants by Slice D, and they MUST NOT be copied into a
real deployment binding by this document.

## f. Lifecycle posture

Slice D is an `identity` (privileged) / `docs` mutation under Feature
001 FR-008. Consequences for this pattern document:

1. Slice D authoring is permitted under the Source-ratified Slice D
   implementation envelope. Source ratification of that envelope is
   the only authorization for Slice D authoring; this document itself
   does not authorize downstream identity instantiation.
2. Instantiating a real reviewer identity record requires a separate
   per-batch privileged envelope, authored under Feature 004 scope,
   with its own Source ratification.
3. Author/approver separation applies to every step: the actor who
   authors a future reviewer identity record MUST NOT be the actor
   who ratifies that record.
4. Author/approver separation also applies to the reviewer-of-the-
   mutation relationship: the reviewer who authors review evidence
   on a mutation MUST NOT also be its ratifier.
5. The reviewer identity is not Source. A reviewer's role category
   is `reviewer`, not `ratifier` or `source`. Conflating the two is
   an authority conflict per Feature 002 FR-018 and triggers the
   halt/escalation path in
   [`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md).

## g. Cross-references

- Generic review-evidence template:
  [`./REVIEW_EVIDENCE_TEMPLATE.md`](./REVIEW_EVIDENCE_TEMPLATE.md).
- Review gate that consumes review evidence and reviewer identity
  records: [`./REVIEW_GATE.md`](./REVIEW_GATE.md).
- Backlog row for Slice D: [`./BACKLOG.md`](./BACKLOG.md) §c.4.
- Sprint 0 exit gates #7 (governed roles) and #10 (QA / review
  evidence format):
  [`../../specs/sprint-0-minimum-viable-delivery-system/README.md`](../../specs/sprint-0-minimum-viable-delivery-system/README.md)
  §4.

## h. Acceptance posture

This document satisfies the Slice D implementation envelope's
reviewer-identity-pattern requirements:

- Defines a generic reviewer identity record pattern rather than an
  instantiated identity.
- States that upstream Creator Engine does not instantiate a real
  reviewer identity in Slice D, and that concrete bindings are
  deployment-time overlay decisions.
- States that a reviewer identity may author review evidence only
  within the mutation classes and repositories named by its ratified
  identity record.
- States that reviewer evidence is advisory/governance evidence and
  is **not Source ratification**.
- States the default rule that the reviewer identity MUST NOT author
  the mutation it reviews unless Source separately ratifies a narrow
  exception.
- States that privileged classes still require Source ratification.
- States that author/approver separation applies.
- Enumerates the required record fields (or Feature 001 equivalents)
  the pattern requires, with explicit upstream-binding constraints
  marking deployment-time values and placeholders.
- Names the forbidden content surfaces (real account names, real
  installation ids, real actor ids, real app slugs, emails, tokens,
  secrets, machine-local absolute paths).
