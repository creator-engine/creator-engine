# Review Gate (Generic Definition)

**Status**: Slice D authored draft. This document defines the
**review gate** for Creator Engine governed work: when independent
review evidence is required, which reviewer identity authorizes the
evidence, how the evidence is evaluated, and the standing invariant
that review evidence is never Source ratification.

Part of the **minimum repo-native delivery control plane** and
**not a Jira clone**. Layered onto, and subordinate to, the Feature
001 substrate, the Feature 002 operating model, and the existing
delivery-view DoR/DoD documents.

## a. Purpose

The review gate is the delivery-view checkpoint at which a governed
work item must carry **independent review evidence** before it can be
considered eligible for Source ratification. The gate does **not**
itself ratify the underlying mutation; it produces and consumes
evidence used by Source review.

The gate answers the ten questions enumerated by the Slice D
implementation envelope, restated in §c through §m below:

1. when independent review evidence is required (§c);
2. which identity record authorizes the reviewer (§d);
3. which artifacts are in scope for review (§e);
4. which mutation classes are being reviewed (§f);
5. which prohibited surfaces must be checked (§g);
6. what verdict values are valid (§h);
7. what happens on blocking findings (§i);
8. what happens if the reviewer identity is missing or not ratified (§j);
9. how review evidence is stored or referenced (§k);
10. who ratifies the underlying change after review evidence exists (§l).

## b. Source-of-truth relationship

| Upstream source of truth | Role |
|---|---|
| [`./REVIEWER_IDENTITY_REQUIREMENTS.md`](./REVIEWER_IDENTITY_REQUIREMENTS.md) | Reviewer identity record pattern that authorizes who may author review evidence. |
| [`./REVIEW_EVIDENCE_TEMPLATE.md`](./REVIEW_EVIDENCE_TEMPLATE.md) | Generic markdown-equivalent template for the evidence artifacts the gate consumes. |
| [`./DEFINITION_OF_READY.md`](./DEFINITION_OF_READY.md) §b, §c | Ready criteria, privileged-class rule, author/approver separation. |
| [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §b.4, §b.5 | Independent review evidence where applicable; review is not ratification; privileged classes require Source ratification. |
| [`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md) §b–§e | Reviewer authors review evidence; reviewer does not ratify. Identity is privileged. Author/approver separation. Authority-conflict halt/escalation path. |
| Feature 001 FR-008 | Privileged-class enumeration. |
| Feature 001 FR-007 | Author/approver separation. |
| Feature 002 FR-018 | Authority-conflict halt/escalation path. |
| [`../../specs/sprint-0-minimum-viable-delivery-system/README.md`](../../specs/sprint-0-minimum-viable-delivery-system/README.md) §4 exit gates #7 and #10 | Sprint 0 exit gates for governed roles and QA / review evidence format. |

Where this document and any upstream source disagree, the upstream
source of truth controls until Source ratifies a correction.

## c. When independent review evidence is required

The review gate applies to every governed mergeable unit unless
Source explicitly waives the requirement for a named batch under an
explicit envelope clause. In general:

1. Future mergeable units SHOULD carry **independent review evidence**
   before they advance past the review gate.
2. Slice-D-and-earlier delivery-view doc batches that landed before
   the review gate was authored MAY have advanced under prior
   Source-ratified envelope wording; this does not retroactively
   require review evidence on already-merged units.
3. A reviewer who is also the author of the mutation is not
   independent. Author/approver separation (Feature 001 FR-007) and
   the reviewer-not-author default in
   [`./REVIEWER_IDENTITY_REQUIREMENTS.md`](./REVIEWER_IDENTITY_REQUIREMENTS.md)
   §c.5 apply.
4. Source MAY explicitly waive the independent-review requirement for
   a named batch. The waiver MUST be recorded in the batch's
   Source-ratified envelope. A waiver is not implied by silence and
   is not implied by a `no_blocking_findings` verdict from any agent.
5. Missing review evidence on a batch that requires it blocks
   advancement past the review gate; the next governed action is
   either authoring the evidence under the required reviewer identity
   or requesting a Source-ratified waiver.

## d. Which identity record authorizes the reviewer

A reviewer may author governed review evidence only if a **ratified
reviewer identity record** exists naming that actor. The identity
record:

1. MUST satisfy the pattern in
   [`./REVIEWER_IDENTITY_REQUIREMENTS.md`](./REVIEWER_IDENTITY_REQUIREMENTS.md);
2. MUST carry `role_category: reviewer`;
3. MUST list the evidence-authoring mutation classes (e.g.,
   `governance` or `docs` for the evidence artifact itself), and MUST
   NOT list privileged mutation classes belonging to the change under
   review;
4. MUST have been Source-ratified under its own per-batch privileged
   envelope (Slice D does not instantiate a real reviewer identity;
   instantiation is downstream Feature 004 work).

A reviewer evidence record whose `reviewer_identity_ref` points at a
non-ratified or non-existent identity record fails the gate per §j.

## e. Which artifacts are in scope for review

The artifacts in scope are named by the evidence record's
`reviewed_artifact_refs` and the batch's Source-ratified envelope:

1. The diff range or commit-ish under review
   (`reviewed_diff_or_commit_ref`).
2. The spec/plan/tasks artifacts that authorize the batch.
3. Validator output and any cited attestation paths.
4. Repo-relative paths to artifacts touched by the batch.

Scope is **bounded** by the ratified envelope. A reviewer may not
author evidence on artifacts outside the envelope's allowed-file
boundary unless Source explicitly extends scope. If scope is unclear,
the reviewer's verdict is `scope_boundary_unclear` per §h.

## f. Which mutation classes are being reviewed

The reviewer records the mutation classes the change touches in the
evidence record's `mutation_classes_under_review` array, per
[`../governance/MUTATION_CLASS_MODEL.md`](../governance/MUTATION_CLASS_MODEL.md).

The reviewer's authority to author evidence does not authorize the
reviewer to perform any of those mutation classes outside the
evidence artifact itself. **Privileged mutation classes** —
`deploy`, `governance`, `identity`, `security`, `attestation`, and
`redaction` per Feature 001 FR-008 — remain Source-ratified
regardless of reviewer verdict.

## g. Which prohibited surfaces must be checked

The reviewer affirmatively checks that the change under review does
not mutate, and the evidence body does not claim authority over, any
of the standing prohibited surfaces. The reviewer records the
checked surfaces in `prohibited_surfaces_checked`. At minimum:

| Prohibited-surface label | Check |
|---|---|
| `live_repository_settings` | The change does not, and the reviewer's verdict does not authorize, mutating live repository settings on the source host. |
| `branch_protection` | The change does not, and the verdict does not authorize, mutating live branch protection on the remote repository. |
| `deploy_automation` | The change does not, and the verdict does not authorize, running or modifying deploy automation. |
| `codeowners` | The change does not, and the verdict does not authorize, mutating any CODEOWNERS file. |
| `secrets_or_tokens` | The change does not introduce, leak, or rely on secrets, tokens, credentials, or accounts. |
| `instance_local_paths` | The change does not introduce machine-local absolute paths, local terminal identifiers, local session identifiers, or forensic session-backup paths into governed artifacts. |
| `branch_lifecycle` | The change does not, and the verdict does not authorize, deleting, renaming, or otherwise mutating branches on the source host. |
| `source_host_metadata` | The change does not, and the verdict does not authorize, mutating PR/issue/label/assignment metadata on the source host. |

A finding on any prohibited surface is a `blocking_findings` entry
per §i.

## h. Valid verdict values

The gate accepts only the evidence-only verdict values enumerated in
[`./REVIEW_EVIDENCE_TEMPLATE.md`](./REVIEW_EVIDENCE_TEMPLATE.md) §d:

- `no_blocking_findings`
- `blocking_findings_present`
- `scope_boundary_unclear`
- `cannot_review`

A `no_blocking_findings` verdict means the reviewer observed no
blocking findings within the stated scope; it is **not Source
ratification** and never authorizes merge, deploy, branch deletion,
branch protection mutation, or live repository-settings change. Any
verdict beyond the four above is not a governed verdict under this
gate and is itself a `cannot_review` condition.

## i. What happens on blocking findings

When a reviewer records `blocking_findings_present` (or when any
`blocking_findings` entries appear regardless of verdict):

1. The batch **halts** at the review gate.
2. The next governed action is one of: (a) amendment of the batch
   under its existing Source-ratified envelope, (b) scrap and redo
   under a new Source-ratified envelope, or (c) a Source-directed
   disposition that names a specific path forward.
3. The reviewer MUST NOT escalate by widening their own authority.
   The actor who authors review evidence MUST NOT also ratify the
   mutation under review (Feature 001 FR-007).
4. CI green, an external tracker green check, an agent commentary
   verdict, or a passing validator run MUST NOT substitute for
   addressing the blocking findings.

## j. What happens if the reviewer identity is missing or not ratified

If the reviewer identity record named by
`reviewer_identity_ref` does not exist, has not been Source-ratified,
or does not satisfy the pattern in
[`./REVIEWER_IDENTITY_REQUIREMENTS.md`](./REVIEWER_IDENTITY_REQUIREMENTS.md):

1. The evidence record is not governed under this gate.
2. Advancement past the gate is **blocked** until either (a) a
   ratified reviewer identity authors fresh evidence, or (b) Source
   explicitly waives the requirement for the named batch under an
   explicit envelope clause.
3. The blocker is recorded as the implied next task per
   [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §c.
4. Attempting to advance the batch under unratified reviewer identity
   is an authority conflict per Feature 002 FR-018 and triggers the
   halt/escalation path in
   [`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md).

## k. How review evidence is stored or referenced

Concrete storage paths and machine-readable schemas for review
evidence are **deployment-time overlay decisions** and downstream
Feature 004 work. For Slice D:

1. Evidence is authored against the generic markdown template in
   [`./REVIEW_EVIDENCE_TEMPLATE.md`](./REVIEW_EVIDENCE_TEMPLATE.md).
2. A deployment overlay binds the reviewer identity record's
   `attestation_storage_path` (or an explicit evidence directory
   under the substrate's storage conventions) to the tenant-local
   layout, with Source ratification.
3. Evidence MAY be referenced from a batch's envelope, completion
   report, or post-merge next-task report, as repo-relative paths
   only. Network or tracker URLs are non-canonical per
   [`./README.md`](./README.md) §d.
4. Source ratification artifacts MUST NOT be co-mingled with
   evidence artifacts in a way that obscures the author/approver
   separation contract.

## l. Who ratifies the underlying change after review evidence exists

Review evidence supports Source review of the underlying change; it
does not replace it.

1. After review evidence is recorded, the next governed action for a
   privileged-class batch is a **ratification request to Source** per
   [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §c.5.
2. Source ratification of the underlying change is the only
   authorization that promotes the batch past `Verified` to
   `Ratified` per
   [`./BACKLOG.md`](./BACKLOG.md) §a.
3. For non-privileged classes (`docs`, `code`, `schema`) where
   Source has ratified delegation to a `ratifier` role, the
   `ratifier` may complete ratification under the delegation. The
   delegation itself remains a privileged `governance` decision
   requiring Source ratification.
4. The reviewer who authored the evidence MUST NOT be the ratifier
   of the change.

## m. Standing invariants

The following invariants apply to every use of the review gate:

1. **Review evidence is not Source ratification.** A verdict of
   `no_blocking_findings` is not, and never becomes, ratification.
2. **Privileged mutation classes** remain Source-ratified regardless
   of reviewer verdict. A reviewer cannot waive a privileged gate.
3. **Missing reviewer identity or missing review evidence blocks
   advancement** past the review gate unless Source explicitly
   waives the requirement for that batch.
4. **Blocking findings halt the batch.** Remediation, scrap/redo, or
   Source-directed disposition follows; agent commentary does not.
5. **Author/approver separation applies.** The reviewer is not the
   author of the mutation under review (default rule), and the
   reviewer is not the ratifier of the mutation under review.
6. **Review evidence may support** Nefarious/Hermes scope audit and
   Source review. It is advisory/governance evidence with no merge,
   deploy, branch-protection, or repository-settings authority.
7. **CI / external tracker signals never substitute for Source
   ratification.** A passing workflow, a green tracker check, or an
   agent verdict cannot promote a privileged-class batch past the
   ratification step.

## n. Acceptance posture

This document satisfies the Slice D implementation envelope's
review-gate requirements:

- Answers all ten review-gate questions named by the envelope (§c–§l).
- States the minimum gate semantics:
  - Future mergeable units carry independent review evidence unless
    Source explicitly waives it for a named batch (§c).
  - Missing reviewer identity or missing review evidence blocks
    advancement past the gate (§c, §j).
  - Blocking findings halt the batch (§i).
  - Review evidence may support Nefarious/Hermes scope audit and
    Source review (§m.6).
  - Review evidence **never substitutes for Source ratification**,
    including under a `no_blocking_findings` verdict (§h, §m.1).
  - **Privileged mutation classes** remain Source-ratified regardless
    of reviewer verdict (§f, §m.2).
- States the standing invariants (§m), including the non-ratification
  invariant, the privileged-class invariant, and the
  author/approver-separation invariant.
