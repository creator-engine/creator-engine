# Review Evidence Template (Generic)

**Status**: Slice D authored draft. This document defines a generic
markdown-equivalent **template contract** for independent review
evidence under the Creator Engine delivery control plane. It is not a
machine-readable schema; the JSON/YAML evidence schema is downstream
Feature 004 work and is out of scope for Slice D.

Part of the **minimum repo-native delivery control plane** and
**not a Jira clone**. Layered onto, and subordinate to, the Feature
001 substrate
([`../contracts/identity-record.md`](../contracts/identity-record.md))
and the Feature 002 operating model.

## a. Purpose

A review evidence record makes a single fact answerable from a fresh
clone:

> What did an independent reviewer observe about a specific mutation,
> against which mutation classes and prohibited surfaces, and what was
> their non-ratifying verdict?

The template carries enough information for Source review and for
Nefarious/Hermes scope audit. It is not authoritative ratification.

## b. Source-of-truth relationship

| Upstream source of truth | Role |
|---|---|
| [`./REVIEWER_IDENTITY_REQUIREMENTS.md`](./REVIEWER_IDENTITY_REQUIREMENTS.md) | Reviewer identity pattern that authorizes who may author review evidence. |
| [`./REVIEW_GATE.md`](./REVIEW_GATE.md) | Review-gate definition that names when review evidence is required and how it is evaluated. |
| [`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md) §b–§e | Reviewer writes review evidence; reviewer does not ratify. Author/approver separation. |
| [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §b.4, §b.5 | Independent review evidence where applicable; review is not ratification. |
| Feature 001 FR-008 | Privileged-class enumeration; privileged mutations remain Source-ratified regardless of reviewer verdict. |
| Feature 001 FR-007 | Author/approver separation. |
| [`../../specs/002-canonical-docs-and-operating-model/spec.md`](../../specs/002-canonical-docs-and-operating-model/spec.md) | Review evidence is distinct from ratification; actor/tool examples are not deployment-time bindings. |
| [`../../specs/sprint-0-minimum-viable-delivery-system/README.md`](../../specs/sprint-0-minimum-viable-delivery-system/README.md) §4 exit gate #10 | QA / review evidence format acceptance gate. |

Where this template and any upstream source disagree, the upstream
source of truth controls until Source ratifies a correction.

## c. Required fields

Every governed review evidence record MUST populate the following
fields. Field semantics are intentionally generic and remain
project-, tenant-, runtime-, model-, and harness-agnostic.

| Field | Semantics |
|---|---|
| `evidence_id` | Stable identifier for this evidence record within its storage path. Repo-relative and unique within a tenant overlay. |
| `reviewed_artifact_refs` | Array of repo-relative paths to artifacts under review (spec, plan, tasks, code, docs, validator output, etc.). MUST be non-empty. |
| `reviewed_diff_or_commit_ref` | Reference to the diff range or commit-ish under review. For pre-merge review, the working diff range; for post-merge review, the merged commit-ish. |
| `reviewer_identity_ref` | Repo-relative path to the ratified reviewer identity record under which this evidence is authored. The referenced identity record's `mutation_classes` MUST include the evidence-authoring class used. |
| `reviewer_role_category` | Fixed to `reviewer`. Records with any other `role_category` are not governed review evidence under this template. |
| `review_mode` | Generic enum or free-text policy field describing the mode (e.g., `manual_human`, `manual_agent`, `mixed_human_and_agent`). Concrete tool/model/CLI selection is a deployment-time overlay decision and MUST NOT be hard-coded as an upstream binding here. |
| `review_scope` | Human-readable scope statement: what was in scope and what was out of scope for this evidence. |
| `mutation_classes_under_review` | Array of mutation classes (per [`../governance/MUTATION_CLASS_MODEL.md`](../governance/MUTATION_CLASS_MODEL.md)) that the change under review touches. |
| `prohibited_surfaces_checked` | Array of prohibited-surface labels the reviewer affirmatively checked (e.g., `live_repository_settings`, `branch_protection`, `deploy_automation`, `codeowners`, `secrets_or_tokens`, `instance_local_paths`). |
| `validation_evidence_refs` | Array of repo-relative paths or command-result references the reviewer consulted (validator runs, CI output references, attestation paths). External tracker URLs are non-canonical and MAY appear only as advisory references. |
| `findings` | Free-text body of observations. |
| `blocking_findings` | Array of finding records that, per the review gate, prevent advancement past the gate without remediation. Each entry names the artifact ref, the rule violated, and the recommended remediation. |
| `non_blocking_findings` | Array of finding records that are advisory only (style, future-work suggestions, scope clarifications) and do not, by themselves, prevent advancement. |
| `verdict` | One of the evidence-only values enumerated in §d. |
| `recommended_follow_up` | Free-text recommendations for follow-up work (separate envelopes, future slices, deferred items). |
| `evidence_timestamp` | Evidence timestamp or, where deployment policy requires, a source-controlled timestamp policy reference (e.g., commit timestamp on the evidence file). Machine-local clock values MUST NOT be presented as authoritative. |
| Non-ratification statement | An explicit text statement in the evidence body that **review evidence is not Source ratification** and does not authorize merge, deploy, branch deletion, branch protection mutation, or live repository-settings change. |

The non-ratification statement is mandatory. Its absence is itself a
`blocking_findings` condition under [`./REVIEW_GATE.md`](./REVIEW_GATE.md).

## d. Allowed verdict values

`verdict` is constrained to evidence-only outcomes. These are the
**only** governed verdict values under Slice D:

| Verdict | Meaning |
|---|---|
| `no_blocking_findings` | The reviewer completed the review within the stated scope and observed no blocking findings. Advisory `non_blocking_findings` MAY be present. This verdict is **not Source ratification** and MUST NOT be treated as authorization to merge, deploy, mutate branch protection, mutate repository settings, delete branches, or otherwise advance a privileged class. |
| `blocking_findings_present` | The reviewer observed one or more `blocking_findings`. The review gate halts the batch per [`./REVIEW_GATE.md`](./REVIEW_GATE.md) §g; remediation, scrap/redo, or Source-directed disposition follows. |
| `scope_boundary_unclear` | The reviewer could not determine whether the change under review fits the ratified envelope. The next governed action is a Source clarification, not a verdict override. |
| `cannot_review` | The reviewer is unable to perform the review (missing artifacts, missing reviewer identity record, ratification conflict, authority conflict, or other halt condition). Advancement past the review gate is blocked until the named condition clears. |

The template MUST NOT define, accept, or document any verdict value
that implies the reviewer can ratify, approve merge, waive a
privileged gate, modify branch protection, run or modify deploy
automation, or apply live repository settings. Such values are
contract violations of Feature 001 FR-007 / FR-008 and Feature 002
FR-018.

## e. Markdown body template

The following block is a generic markdown body template. Concrete
fields are stylized as placeholders. A deployment overlay MAY add
fields that are strictly additive and that do not imply ratifying
authority for the reviewer.

```markdown
# Review Evidence — <evidence_id>

- evidence_id: <stable identifier>
- reviewed_artifact_refs:
  - <repo-relative path>
- reviewed_diff_or_commit_ref: <diff range or commit-ish>
- reviewer_identity_ref: <repo-relative path to ratified reviewer identity record>
- reviewer_role_category: reviewer
- review_mode: <manual_human | manual_agent | mixed_human_and_agent>
- review_scope: <one or more sentences naming in-scope and out-of-scope items>
- mutation_classes_under_review:
  - <mutation class>
- prohibited_surfaces_checked:
  - <prohibited-surface label>
- validation_evidence_refs:
  - <repo-relative path or command-result reference>
- evidence_timestamp: <evidence timestamp or source-controlled timestamp reference>

## Findings

<free-text observations>

## Blocking findings

- <artifact ref> — <rule violated> — <recommended remediation>

## Non-blocking findings

- <artifact ref> — <observation> — <advisory follow-up>

## Verdict

<one of: no_blocking_findings | blocking_findings_present | scope_boundary_unclear | cannot_review>

## Recommended follow-up

<free-text recommendations>

## Non-ratification statement

This review evidence is **not Source ratification** and does not
authorize merge, deploy, branch deletion, branch protection mutation,
or live repository-settings change. Privileged mutation classes
remain Source-ratified regardless of this verdict.
```

## f. Forbidden content for this template

A review evidence record produced under this template MUST NOT
contain:

- a hard-coded reviewer product, model, CLI, SaaS account, runner,
  source-host application, bot slug, or QA harness as a normative
  upstream binding (concrete tool/model selection is a deployment-time
  overlay);
- real emails, tokens, secrets, credentials, source-host installation
  ids, durable actor ids, app slugs, or account names;
- machine-local absolute paths, local terminal identifiers, local
  session identifiers, or forensic session-backup paths;
- claims of authority to ratify, approve merge, waive a privileged
  gate, modify branch protection, mutate repository settings, run or
  modify deploy automation, delete or rename branches, or alter
  source-host metadata.

Existing example actor/tool names in upstream anchors remain examples
only. The template MUST NOT promote them into upstream constants or
into deployment-time bindings.

## g. Storage and reference policy

Concrete storage paths for review evidence are **deployment-time
overlay decisions**. Slice D does not select a tenant-level evidence
directory. A deployment overlay binds the reviewer identity record's
`attestation_storage_path` (or an explicit evidence directory under
the substrate's storage conventions) to the tenant-local layout, with
Source ratification of that overlay.

## h. Acceptance posture

This document satisfies the Slice D implementation envelope's review
evidence template requirements:

- Defines a generic markdown-equivalent contract for review evidence
  rather than a machine-readable schema.
- Includes all required fields named by the envelope: `evidence_id`,
  `reviewed_artifact_refs`, `reviewed_diff_or_commit_ref`,
  `reviewer_identity_ref`, `reviewer_role_category`, `review_mode`,
  `review_scope`, `mutation_classes_under_review`,
  `prohibited_surfaces_checked`, `validation_evidence_refs`,
  `findings`, `blocking_findings`, `non_blocking_findings`,
  `verdict`, `recommended_follow_up`, evidence-timestamp policy,
  and an explicit non-ratification statement.
- Constrains `verdict` to evidence-only outcomes:
  `no_blocking_findings`, `blocking_findings_present`,
  `scope_boundary_unclear`, `cannot_review`.
- States explicitly that review evidence is **not Source ratification**
  and does not authorize merge, deploy, branch deletion, branch
  protection mutation, or live repository-settings change.
- Names the forbidden content surfaces and the deployment-time
  overlay boundary.
