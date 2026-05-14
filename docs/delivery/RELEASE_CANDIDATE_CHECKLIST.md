# Release Candidate Checklist

**Status**: Sprint 0 Slice F landed policy. Authored via PR #16 /
`cb7f94a`; delivery-state reconciliation landed via PR #17 /
`5be005b`. This document remains policy-only; it does not implement,
deploy, merge, or ratify.

This document defines what promotes an in-progress governed work
batch to **release-candidate (RC) status** on the delivery view, and
what evidence the RC carries with it before any subsequent merge or
deploy is considered. Part of the **minimum repo-native delivery
control plane** and **not a Jira clone**. Layered onto, and
subordinate to, the Feature 001 substrate, the Feature 002 operating
model, and the existing delivery-view DoR / DoD / review-gate
documents. A fresh clone is sufficient to apply this checklist; no
external tracker credential or network state is required.

## a. Purpose

The RC checklist makes one operational question answerable from a
fresh clone:

> Has this in-progress batch reached the point where Source could
> review it as a candidate for merge, and is its evidence package
> reconstructable from repository artifacts alone?

The RC checklist is **policy authoring**, not deploy automation. It
does not run, sign, publish, or deploy anything; it does not author
merge or deploy approval — those are governed by the sibling
[`./MERGE_APPROVAL_CHECKLIST.md`](./MERGE_APPROVAL_CHECKLIST.md) and
[`./DEPLOYMENT_APPROVAL_POLICY.md`](./DEPLOYMENT_APPROVAL_POLICY.md).
RC status is a **delivery-view bookkeeping state** on the path
toward `Verified` per
[`./BACKLOG.md`](./BACKLOG.md) §a.

## b. Source-of-truth relationship

| Upstream source of truth | Role |
|---|---|
| Feature 001 FR-007 | Author / approver separation: the author of a mutation MUST NOT be its ratifier. |
| Feature 001 FR-008 | Privileged mutation classes (`deploy`, `governance`, `identity`, `security`, `attestation`, `redaction`) require explicit human Source ratification. |
| Feature 001 FR-016 | Ratification flow; required ratifier role per mutation class; valid ratification surfaces. |
| Feature 001 FR-013 / FR-013a / FR-014 | Spec lifecycle and Definition of Done substrate contract. |
| [`./DEFINITION_OF_READY.md`](./DEFINITION_OF_READY.md) §b, §c | Delivery-view readiness criteria and privileged-class rule. |
| [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §b, §c | Done criteria and the invariant that CI verifies but does not ratify. |
| [`./REVIEW_GATE.md`](./REVIEW_GATE.md) §c–§m | When independent review evidence is required; verdict vocabulary; standing invariants. |
| [`./REVIEW_EVIDENCE_TEMPLATE.md`](./REVIEW_EVIDENCE_TEMPLATE.md) | Generic review-evidence template the RC cites. |
| [`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md) §c–§l | Verifier-side scope audit consumed by the RC's evidence package. |
| [`./ASSIGNMENT_ENVELOPE_TEMPLATE.md`](./ASSIGNMENT_ENVELOPE_TEMPLATE.md) | Source-ratified envelope that bounds the batch under review. |
| [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b | Ten post-merge completion-report fields the RC's evidence aligns with. |
| [`./BACKLOG.md`](./BACKLOG.md) §a | Delivery-view status vocabulary, including `Verified` and `Ratified`. |
| [`../../specs/sprint-0-minimum-viable-delivery-system/README.md`](../../specs/sprint-0-minimum-viable-delivery-system/README.md) §4 exit gate #11 | Sprint 0 exit gate: release / merge / deploy governance is documented. |
| [`../devops/RELEASE_AND_DEPLOYMENT_STRATEGY.md`](../devops/RELEASE_AND_DEPLOYMENT_STRATEGY.md) | Canonical release / deployment strategy this policy is layered onto. |
| Sibling Slice F docs ([`./MERGE_APPROVAL_CHECKLIST.md`](./MERGE_APPROVAL_CHECKLIST.md), [`./DEPLOYMENT_APPROVAL_POLICY.md`](./DEPLOYMENT_APPROVAL_POLICY.md), [`./ROLLBACK_AND_POST_RELEASE_EVIDENCE.md`](./ROLLBACK_AND_POST_RELEASE_EVIDENCE.md), [`./RELEASE_DEPLOY_GOVERNANCE.md`](./RELEASE_DEPLOY_GOVERNANCE.md)) | Slice F policy authoring envelope; this document is one of four content docs bound by the index. |

Where this document and any upstream source disagree, the upstream
source controls until Source ratifies a correction.

## c. What promotes a batch to release-candidate status

A governed batch promotes to **release-candidate** on the delivery
view when **every** condition below is satisfied. Each condition is
verifiable from the repository alone; instance-local facts MUST NOT
be relied upon.

### c.1 The batch was consumed under a Source-ratified envelope

The batch's Assignment Envelope is Source-ratified per Feature 001
FR-016 and instantiated per
[`./ASSIGNMENT_ENVELOPE_TEMPLATE.md`](./ASSIGNMENT_ENVELOPE_TEMPLATE.md).
The envelope's `mutation_classes`, `allowed_create_paths`,
`allowed_update_paths`, `prohibited_surfaces`, `stop_condition`, and
`ratifier` fields are present and unambiguous. A batch consumed
under an unratified or implicit envelope is NOT a release candidate.

### c.2 The batch reached its declared stop line without crossing it

The consumer stopped at the envelope's named stop condition without
staging, committing, pushing, opening or mutating a PR, merging,
deleting a branch, removing a worktree, mutating repository
settings, bypassing hooks, or otherwise crossing the stop line. The
no-mechanics conditions in
[`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md) §e are
satisfied.

### c.3 Validation evidence passes (or skipped checks are named with a rationale)

The validation commands or validation plan declared at readiness
(per [`./DEFINITION_OF_READY.md`](./DEFINITION_OF_READY.md) §b.8)
have been run and their outputs captured. Failing checks MUST be
either remediated under the envelope's authorship or surfaced as
blocking findings; skipped checks MUST be named with an explicit
rationale per
[`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §b.2. Where a
Creator Engine validator run applies, its exit status and any
failure output are recorded; where no CI workflow is wired for the
batch's mutation class, local-validation evidence is named per
[`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b.3.

### c.4 The review gate has been evaluated per `REVIEW_GATE.md`

Independent review evidence per
[`./REVIEW_GATE.md`](./REVIEW_GATE.md) §c–§l is recorded against the
batch, or Source has explicitly waived the requirement for this
named batch in the envelope. The reviewer identity record is
ratified per
[`./REVIEWER_IDENTITY_REQUIREMENTS.md`](./REVIEWER_IDENTITY_REQUIREMENTS.md);
the reviewer is not the author of the mutation
(Feature 001 FR-007); the verdict is one of the four values
enumerated in
[`./REVIEW_EVIDENCE_TEMPLATE.md`](./REVIEW_EVIDENCE_TEMPLATE.md) §d.

A `no_blocking_findings` verdict on the review evidence is NOT, and
never becomes, Source ratification of the mutation
([`./REVIEW_GATE.md`](./REVIEW_GATE.md) §m.1).

### c.5 The scope audit has been completed per `SCOPE_AUDIT_CHECKLIST.md`

The verifier-side scope audit in
[`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md) §c–§l has
been performed: the changed-file set is the union of the envelope's
allowed creates and directly needed allowed updates; no prohibited
surface was mutated; `git diff --check` is clean; stale-language
scans return the expected results; markdown link / reference sanity
holds; branch / worktree isolation is preserved; the auditor's
report-back states explicitly that the audit is verification
evidence and not Source ratification.

### c.6 A ratification record exists per Feature 001 FR-016

A repository-visible ratification record satisfying Feature 001
FR-016 and FR-020a names Source as the ratifier of the envelope and
identifies the batch by its envelope id, base commit, and intended
scope. For privileged-class batches the ratifier MUST be Source per
FR-008; agent-authored review text, CI green, an external tracker
green check, or a "go ahead" message on a non-designated surface
MUST NOT substitute (FR-017, FR-018,
[`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §c).

The ratification record cited for RC status authorizes the envelope.
It does **not**, by itself, authorize merge, deploy, branch
deletion, or any repository-setting mutation; those authorizations
are sibling decisions governed by
[`./MERGE_APPROVAL_CHECKLIST.md`](./MERGE_APPROVAL_CHECKLIST.md) and
[`./DEPLOYMENT_APPROVAL_POLICY.md`](./DEPLOYMENT_APPROVAL_POLICY.md).

### c.7 The evidence package is reconstructable from the repository alone

A fresh clone is sufficient to read every field cited above: the
envelope, the changed-file set, the validation outputs, the review
evidence, the scope-audit report-back, and the ratification record.
Instance-local facts (absolute filesystem paths on a specific
operator's clone, terminal pane identifiers, local session queues,
secrets, tokens) MUST NOT appear in the evidence package; only
merged PR numbers in canonical-branch commit subjects MAY be cited
as historical evidence per
[`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §e.

## d. Required evidence fields for a release candidate

Every release candidate carries the evidence below. The fields align
with the ten post-merge fields in
[`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b without
amending or replacing them; the RC is **pre-merge** and therefore
does not yet carry merge identification, post-merge documentation
impact, or post-merge cleanup state.

| Field | Description | Source-of-truth check |
|---|---|---|
| RC identification | Envelope id, base commit, source branch, batch id, the dominant mutation class, and the declared ratifier. | Envelope per [`./ASSIGNMENT_ENVELOPE_TEMPLATE.md`](./ASSIGNMENT_ENVELOPE_TEMPLATE.md); backlog row per [`./BACKLOG.md`](./BACKLOG.md). |
| Scope summary | One-paragraph summary of what changed, what intentionally did not change, and the surfaces that were declared `prohibited_surfaces`. | Envelope; backlog row. |
| Validation evidence | Commands run, exit statuses, and any check skipped with rationale. | [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §b.2; [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b.3. |
| Review evidence | Reviewer identity record reference, reviewed-diff range, mutation classes under review, prohibited surfaces checked, verdict, and any blocking findings. | [`./REVIEW_GATE.md`](./REVIEW_GATE.md); [`./REVIEW_EVIDENCE_TEMPLATE.md`](./REVIEW_EVIDENCE_TEMPLATE.md). |
| Scope-audit evidence | Verifier report-back per §c.5 above, including changed-file boundary comparison, prohibited-surface check, no-mechanics check, `git diff --check`, stale-language scans, markdown link sanity, and branch / worktree isolation. | [`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md) §c–§l. |
| Governance evidence | Mutation classes touched and the ratification record per Feature 001 FR-016 / FR-020a. | Feature 001 FR-008 / FR-016 / FR-020a; [`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md). |
| Readiness impact | Sprint 0 exit gate(s) that the batch advances or that remain blocked. | [`../../specs/sprint-0-minimum-viable-delivery-system/README.md`](../../specs/sprint-0-minimum-viable-delivery-system/README.md) §4. |
| Deferred work | Items intentionally deferred by the batch, with the owning future slice or feature. | [`./BACKLOG.md`](./BACKLOG.md); [`./DEPENDENCIES.md`](./DEPENDENCIES.md). |
| Cleanup posture | Whether the feature branch is to be retained, deleted, or requires Source approval before deletion (default: retention pending explicit approval). | [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §b.9; [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b.10. |

Where a field overlaps with the ten post-merge fields, this checklist
authors a **pre-merge** view of the same evidence; the post-merge
report ([`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b)
adds the post-merge-only fields (merge identification, post-merge
documentation impact, post-merge cleanup state).

## e. What RC status does NOT do

To make the boundary unambiguous, the following are explicitly
**not** authorized by reaching release-candidate status:

1. RC status does NOT authorize merge. Merge is governed by
   [`./MERGE_APPROVAL_CHECKLIST.md`](./MERGE_APPROVAL_CHECKLIST.md)
   and requires Source ratification of the merge itself per Feature
   001 FR-008 / FR-016.
2. RC status does NOT authorize deploy. Deploy is governed by
   [`./DEPLOYMENT_APPROVAL_POLICY.md`](./DEPLOYMENT_APPROVAL_POLICY.md);
   no deployment targets or environments currently exist in this
   repository (see §d there), and any future deploy mutation
   requires Source-ratified authority per Feature 001 FR-008.
3. RC status does NOT authorize branch deletion, force-push,
   live-repository-settings mutation, branch-protection mutation,
   or any `.github/` or CODEOWNERS change. Those are separately
   ratifiable privileged actions per Feature 001 FR-008 and per
   [`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md) §e.
4. RC status does NOT amend the Feature 001 spec-status lifecycle.
   It is a delivery-view bookkeeping marker on the path toward
   `Verified` / `Ratified` per
   [`./BACKLOG.md`](./BACKLOG.md) §a; the canonical lifecycle
   continues to use Feature 001 FR-013a values.
5. RC status is NOT recorded on the canonical branch. It is a
   pre-merge state of a feature branch / worktree; canonical-branch
   advancement remains gated on merge approval per
   [`./MERGE_APPROVAL_CHECKLIST.md`](./MERGE_APPROVAL_CHECKLIST.md)
   and on Source ratification of that merge.

## f. Standing invariants

The following invariants apply to every release candidate:

1. **This checklist authors policy, not deploy automation.** Nothing
   in this document executes, signs, publishes, or deploys an
   artifact; nothing here mutates a remote branch, an environment,
   or repository settings. Deploy execution is Feature 006 surface
   per [`../product/ROADMAP.md`](../product/ROADMAP.md) §f, behind a
   future Source-ratified privileged envelope.
2. **Release-candidate status is not Source ratification of any
   mutation.** Reaching RC status confirms that the batch's
   evidence is in place; it does not, and never becomes,
   authorization to merge, deploy, delete branches, or mutate
   repository settings.
3. **Review evidence is not Source ratification.** A
   `no_blocking_findings` verdict on the review evidence is review
   evidence, not ratification
   ([`./REVIEW_GATE.md`](./REVIEW_GATE.md) §m.1).
4. **CI verifies; CI does not ratify.** CI green status MAY be cited
   as validation evidence per
   [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §c.1; it
   does not satisfy Feature 001 FR-008 ratification on its own.
5. **Author / approver separation applies.** The actor who authored
   the mutation MUST NOT be its ratifier (Feature 001 FR-007); the
   reviewer of the mutation MUST NOT be its ratifier
   ([`./REVIEW_GATE.md`](./REVIEW_GATE.md) §m.5).
6. **Privileged mutation classes remain Source-only.** Even when
   RC evidence is complete, `deploy`, `governance`, `identity`,
   `security`, `attestation`, and `redaction` mutations remain
   Source-only per Feature 001 FR-008.
7. **A fresh clone is sufficient to evaluate RC status.** Evidence
   that requires an external tracker credential, a chat surface,
   or a specific operator's environment is not RC evidence under
   this checklist; cf.
   [`./README.md`](./README.md) §d.

## g. Acceptance posture for Slice F

This document satisfies the Slice F implementation envelope's
release-candidate-checklist requirements:

- Defines what promotes an in-progress batch to release-candidate
  status (§c.1–§c.7), including validator pass, review-gate state
  per [`./REVIEW_GATE.md`](./REVIEW_GATE.md), scope audit per
  [`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md), and a
  ratification record per Feature 001 FR-016.
- Enumerates the required evidence fields a release candidate
  carries (§d), aligned with the ten post-merge fields in
  [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b without
  amending them.
- States explicitly what RC status does NOT do (§e), including no
  merge authorization, no deploy authorization, no branch-deletion
  authorization, and no amendment of the Feature 001 lifecycle.
- States explicitly that **this checklist authors policy, not
  deploy automation** (§f.1).
- Carries an explicit non-ratification statement throughout (§e,
  §f.2, §f.3, §f.4, §f.6) so reviewers cannot reasonably mistake RC
  status for Source ratification of a mutation.
