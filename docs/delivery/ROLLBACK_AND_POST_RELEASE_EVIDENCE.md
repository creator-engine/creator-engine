# Rollback and Post-Release Evidence

**Status**: Sprint 0 Slice F landed policy. Authored via PR #16 /
`cb7f94a`; delivery-state reconciliation landed via PR #17 /
`5be005b`. This document remains policy-only; it does not implement,
deploy, merge, or ratify.

This document records rollback decision criteria and the
post-release evidence expectations for Creator Engine governed
work. It is layered onto, and does **not amend**, the ten
post-merge fields in
[`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b. Automated
rollback mechanics are deferred to Feature 006 per
[`../product/ROADMAP.md`](../product/ROADMAP.md) §f. Part of the
**minimum repo-native delivery control plane** and **not a Jira
clone**. A fresh clone is sufficient to apply this document; no
external tracker credential or network state is required.

## a. Purpose

This document makes two operational facts answerable from a fresh
clone:

> 1. Who decides on a rollback, on what evidence, and under what
>    governance authority?
> 2. What post-release evidence is expected after a merge or a
>    (future) deploy lands, and where does that evidence live
>    without amending the canonical post-merge protocol?

Rollback in v0.1 is a **policy concern**, not an automation
concern. The Creator Engine v0.1 substrate names `deploy` as a
privileged mutation class per Feature 001 FR-008 but does not
implement deploy or rollback automation; both are Feature 006
surface per
`./DEPENDENCIES.md` §d.4. This document
authors the policy that any future automation will obey; it does
not, and never becomes, a rollback mechanic.

## b. Source-of-truth relationship

| Upstream source of truth | Role |
|---|---|
| Feature 001 FR-007 | Author / approver separation: the actor who authored the mutation MUST NOT be its ratifier — including any reopen / revert / rollback ratification. |
| Feature 001 FR-008 | Privileged mutation classes (including `deploy`); rollback of a privileged-class mutation is itself a privileged-class action. |
| Feature 001 FR-016 / FR-020a | Ratification flow; ratification record storage format. |
| Feature 001 FR-013a / FR-014 | Spec lifecycle and Definition of Done substrate contract; reopening a ratified item is a privileged amendment. |
| Feature 002 FR-013 | Verifies-not-ratifies invariant: CI / agent evidence is verification, never ratification. |
| [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §b, §c, §e.3 | Done criteria; CI verifies, CI does not ratify; a `Done` item may be reopened only by a Source-ratified amendment. |
| [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b, §d, §e | Ten post-merge completion-report fields; post-merge update procedure; prohibited content. |
| [`./REVIEW_GATE.md`](./REVIEW_GATE.md) §i, §m | What happens on blocking findings; standing invariants. |
| [`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md) §c–§l | Verifier-side scope audit; verification evidence. |
| `./RISK_REGISTER.md` §c.3, §c.8 | R-003 (skipping Source ratification because CI / review passed); R-008 (cleanup deleting branches without approval). |
| Sibling Slice F docs ([`./RELEASE_CANDIDATE_CHECKLIST.md`](./RELEASE_CANDIDATE_CHECKLIST.md), [`./MERGE_APPROVAL_CHECKLIST.md`](./MERGE_APPROVAL_CHECKLIST.md), [`./DEPLOYMENT_APPROVAL_POLICY.md`](./DEPLOYMENT_APPROVAL_POLICY.md), [`./RELEASE_DEPLOY_GOVERNANCE.md`](./RELEASE_DEPLOY_GOVERNANCE.md)) | Slice F policy authoring envelope; this document is one of four content docs bound by the index. |
| [`../devops/RELEASE_AND_DEPLOYMENT_STRATEGY.md`](../devops/RELEASE_AND_DEPLOYMENT_STRATEGY.md) | Canonical release / deployment strategy this policy layers onto. |
| [`../product/ROADMAP.md`](../product/ROADMAP.md) §f | Feature 006 scope; release / deployment governance and rollback automation deferral. |
| [`../../specs/sprint-0-minimum-viable-delivery-system/README.md`](../../specs/sprint-0-minimum-viable-delivery-system/README.md) §4 exit gate #11; §5 Slice F acceptance | Sprint 0 exit gate and Slice F acceptance criteria. |

Where this document and any upstream source disagree, the upstream
source controls until Source ratifies a correction.

## c. Rollback decision criteria

A rollback is the action of reverting, on the canonical branch or
on a (future) deployed environment, a change whose evidence has
become unreliable, whose scope was wider than ratified, or whose
post-merge behaviour violates a Creator Engine substrate
invariant. Rollback decisions in v0.1 follow the criteria below.

### c.1 Who decides

1. The rollback ratifier is **Source** for any rollback that
   touches a privileged mutation class (`deploy`, `governance`,
   `identity`, `security`, `attestation`, `redaction` per Feature
   001 FR-008). A rollback of a privileged-class mutation is
   itself a privileged-class action; agents cannot ratify it.
2. For non-privileged classes (`docs`, `code`, `schema`), in v0.1
   Phase 1 Source remains the operational ratifier of rollback
   per
   [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §b.5; a
   Source-delegated `ratifier` may ratify a rollback only once
   Source has explicitly ratified that delegation.
3. The actor who authored the mutation MUST NOT be its rollback
   ratifier (Feature 001 FR-007). The reviewer of the original
   mutation MUST NOT be its rollback ratifier
   ([`./REVIEW_GATE.md`](./REVIEW_GATE.md) §m.5). The independent
   verifier of the original mutation MUST NOT be its rollback
   ratifier
   ([`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md)
   §k.4).
4. A "go ahead" to roll back on a non-designated surface MUST
   NOT count as rollback authorization (Feature 001 FR-018).
5. A passing CI run, an agent verdict, or an external tracker
   check MUST NOT, by itself, authorize a rollback (Feature 002
   FR-013).

### c.2 On what evidence

A rollback decision MUST be supported by evidence reconstructable
from the repository. At minimum:

1. The identifier of the mutation being rolled back: the
   canonical-branch merge commit SHA (and PR number visible in
   the merge commit subject, if any), the envelope id, and the
   dominant mutation class.
2. The triggering finding: a named defect, a scope-audit failure
   surfaced after merge, a substrate-invariant violation, a
   redaction-gate or attestation-gate failure, or a Source-named
   condition that requires reversion.
3. The proposed rollback scope: revert commit(s), revert range,
   revert mechanic (revert commit vs. forward-fix), and any
   secondary cleanup that the rollback implies. The proposed
   scope itself becomes the next envelope's
   `allowed_create_paths` / `allowed_update_paths`.
4. The post-rollback verification plan: validation commands the
   rollback's post-merge report will run, the review-gate
   posture, and the scope-audit posture.

### c.3 Under what governance authority

A rollback is governed by the same authority gates that govern any
other mutation in the affected class:

1. The envelope authoring the rollback is Source-ratified per
   Feature 001 FR-016 before the rollback mechanic is performed.
2. Author / approver separation is preserved (Feature 001 FR-007).
3. Independent review evidence is recorded against the rollback
   envelope where applicable per
   [`./REVIEW_GATE.md`](./REVIEW_GATE.md) §c, or Source
   explicitly waives the requirement.
4. The scope audit per
   [`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md)
   §c–§l runs against the rollback envelope just as against any
   other batch.
5. The post-merge report of the rollback uses all ten fields in
   [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b.

### c.4 Rollback of a (future) deploy

Because no deployment targets currently exist
([`./DEPLOYMENT_APPROVAL_POLICY.md`](./DEPLOYMENT_APPROVAL_POLICY.md)
§e), there is no live deploy to roll back in v0.1. The policy
below applies the moment any deployment target is first declared
under a Source-ratified Feature 006 envelope:

1. A deploy rollback is itself a `deploy`-class mutation per
   Feature 001 FR-008 and is **Source-only** per
   [`./DEPLOYMENT_APPROVAL_POLICY.md`](./DEPLOYMENT_APPROVAL_POLICY.md)
   §c.
2. A rollback that touches credential / token issuance or
   revocation, governance, security, identity, attestation, or
   redaction surfaces is similarly Source-only per Feature 001
   FR-008.
3. Automated rollback hooks (if and when Feature 006 instantiates
   them) MUST NOT bypass §c.1's ratification requirement; an
   agent triggering an automated rollback is performing the
   `deploy`-class action and the Source ratification of that
   action is required just as for a forward deploy.
4. A rollback decision is recorded as a ratification record per
   Feature 001 FR-016 / FR-020a; the record cites the original
   deploy / merge SHA being reverted and the rollback target.

## d. Post-release evidence layered onto the ten post-merge fields

The ten post-merge fields in
[`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b are
**unamended** by Slice F. Post-release evidence expectations are
layered **on top of** the existing fields, populating them with
release-specific detail without renaming, reordering, or replacing
them. The mapping is:

| Post-merge field (NEXT_TASK_PROTOCOL §b) | Slice F post-release expectation layered on top |
|---|---|
| §b.1 Merge identification | PR number (when present), source / target branch, merge commit SHA, and the batch id whose release / deploy this merge advances. For a (future) deploy that is not itself a merge, the equivalent identifier is the canonical-branch SHA being deployed and the (future) release record id. |
| §b.2 Scope summary | What changed and what intentionally did not change. For a release-track merge: the release-candidate identity carried from [`./RELEASE_CANDIDATE_CHECKLIST.md`](./RELEASE_CANDIDATE_CHECKLIST.md) §d. For a (future) deploy: the environment id, the artifact id, and the explicit non-mutation of any sibling environment. |
| §b.3 Validation evidence | The pushed current-head SHA and required Validate run URL/status bound to that exact head (or required synthetic merge-group head), plus optional targeted author checks. For a (future) deploy this would additionally include the deploy-time checks Feature 006 declares. Local full-suite transcripts are not gate evidence. |
| §b.4 Governance evidence | Mutation classes touched and the Source ratification record per Feature 001 FR-016. For release-track merges: the merge-approval ratification. For a (future) deploy: the deploy ratification per [`./DEPLOYMENT_APPROVAL_POLICY.md`](./DEPLOYMENT_APPROVAL_POLICY.md) §c.3, distinct from any antecedent merge ratification. |
| §b.5 Scope audit | The verifier scope audit per [`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md), confirming no prohibited surface was mutated. For a (future) deploy this expands to: no environment outside the ratified target was touched; no live repository setting or branch protection was mutated. |
| §b.6 Documentation impact | Any canonical document, source-of-truth artifact, or contract changed or requiring follow-up. For release-track merges this includes Slice F documents themselves if they evolve (which is itself a privileged `governance` envelope per Feature 001 FR-008). |
| §b.7 Deferred work | Items explicitly deferred by this release / deploy. For Slice F-adjacent merges this typically includes Feature 006 execution-side work that remains `Deferred` per `./DEPENDENCIES.md` §d.4. |
| §b.8 Readiness impact | Sprint 0 exit gates advanced or still blocked. For a release-track merge under Slice F: gate #11 (release / merge / deploy governance documented) advances. |
| §b.9 Immediate next-task recommendation | One next governed task with rationale. After a release-track merge under Slice F, the typical next recommendation is post-merge reconciliation of delivery-view artifacts, then a Source-directed decision on the next batch — not a deploy (because no deployment targets exist). |
| §b.10 Cleanup state | Branch / worktree state; whether the feature branch is to be deleted, retained, or requires Source approval before deletion. Default posture is retention pending explicit approval per [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §b.9 and `./RISK_REGISTER.md` §c.8. |

The mapping above is **descriptive guidance**, not a schema
amendment. The binding requirement remains that every post-merge
report fills out all ten fields in
[`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b in order;
the Slice F expectations live as content inside those fields.

A release-track batch that also touches a (future) deploy will
carry **two** ratification records under §b.4: one for the merge
and one for the deploy. The two MUST NOT be conflated; merge
authorization is not deploy authorization per
[`./DEPLOYMENT_APPROVAL_POLICY.md`](./DEPLOYMENT_APPROVAL_POLICY.md)
§g.5.

## e. Defect discovered post-merge — interaction with DoD lifecycle

A defect, scope-audit failure, redaction violation, or
substrate-invariant violation discovered after a batch has been
marked `Done` interacts with
[`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §e.3 as
follows:

1. A `Done` item MAY be reopened only by a Source-ratified
   amendment
   ([`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §e.3).
   Reopening a ratified item is a privileged `governance`-class
   action per Feature 001 FR-008; agents cannot reopen it
   unilaterally.
2. The reopening envelope names the defect, the affected mutation
   class, the proposed remediation (forward-fix, revert, or
   forward-fix-plus-revert), and the post-remediation verification
   plan. The envelope is Source-ratified per Feature 001 FR-016.
3. The delivery-view status of the item moves from `Done` back to
   `In Progress` or `Blocked` per
   `./BACKLOG.md` §a and is reflected on the
   Kanban per
   [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §d.2.
4. The Feature 001 spec-status lifecycle is updated under its own
   governed process (FR-013a). The delivery view does not skip,
   backfill, or amend the canonical lifecycle per
   `./BACKLOG.md` §a and the lifecycle-confusion
   risk R-005 in
   `./RISK_REGISTER.md` §c.5.
5. The remediation batch carries its own ratification record per
   Feature 001 FR-016 / FR-020a; it is not authorized by the
   original batch's ratification record.
6. The remediation post-merge report uses all ten fields in
   [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b and
   the post-release expectations layered in §d above.

## f. Automated rollback deferred to Feature 006

Automated rollback (rollback hooks, automated revert pipelines,
deploy-system rollback APIs, environment failover automation,
canary-driven auto-revert, etc.) is **Feature 006** surface and
remains deferred. In v0.1:

1. No rollback automation is wired in this repository.
2. No release agent identity is instantiated (the Slice D pattern
   in
   [`./REVIEWER_IDENTITY_REQUIREMENTS.md`](./REVIEWER_IDENTITY_REQUIREMENTS.md)
   is generic; it is not a release or rollback agent).
3. No GitHub environment, deploy job, or rollback workflow is
   defined.
4. When Feature 006 later instantiates rollback automation under
   its own Source-ratified privileged envelope, the automation
   MUST obey §c above: the ratifier remains Source for any
   privileged-class rollback; author / approver separation is
   preserved; agent-triggered rollbacks are agent-performed
   actions that still require Source-ratified authority.

## g. Standing invariants

The following invariants apply to every rollback and to every
post-release evidence record:

1. **This slice documents policy.** It does not, and never
   becomes, a rollback mechanic; it does not amend the ten
   post-merge fields in
   [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b.
2. **A rollback of a privileged-class mutation is itself a
   privileged-class action** and is Source-only per Feature 001
   FR-008.
3. **Author / approver separation applies to rollback**: the
   author of the original mutation MUST NOT be the ratifier of
   its rollback (Feature 001 FR-007).
4. **CI verifies; CI does not ratify** — including for rollback
   evidence (Feature 002 FR-013,
   [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §c).
5. **Review evidence is not Source ratification** — including for
   rollback evidence
   ([`./REVIEW_GATE.md`](./REVIEW_GATE.md) §m.1).
6. **A `Done` item is reopened only by a Source-ratified
   amendment**
   ([`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §e.3).
7. **Automated rollback is deferred to Feature 006** (§f). Until
   then, rollback in v0.1 is a manual governance action under a
   Source-ratified envelope.
8. **Instance-local facts MUST NOT enter rollback or
   post-release evidence** per
   [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §e. A
   fresh clone is sufficient to evaluate any rollback claim.

## h. Acceptance posture for Slice F

This document satisfies the Slice F implementation envelope's
rollback-and-post-release-evidence requirements:

- States rollback decision criteria: who decides (§c.1), on what
  evidence (§c.2), under what governance authority (§c.3), and
  for a future deploy specifically (§c.4).
- Layers post-release evidence expectations onto the ten
  post-merge fields in
  [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b
  **without amending those fields** (§d).
- Names the defect-discovered-post-merge interaction with the
  Definition-of-Done lifecycle (§e), preserving Feature 001
  FR-013a lifecycle rules and
  [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §e.3.
- States that automated rollback is deferred to Feature 006
  (§f) per
  [`../product/ROADMAP.md`](../product/ROADMAP.md) §f and
  `./DEPENDENCIES.md` §d.4.
- Carries an explicit non-ratification statement throughout (§a,
  §c.1.5, §c.4.3, §g.1, §g.4, §g.5, §g.7) so reviewers cannot
  reasonably mistake any rollback policy artifact, CI verdict,
  reviewer verdict, or post-release evidence record for Source
  ratification of a rollback, merge, or deploy.
