# Merge Approval Checklist

**Status**: Sprint 0 Slice F landed policy. Authored via PR #16 /
`cb7f94a`; delivery-state reconciliation landed via PR #17 /
`5be005b`. This document remains policy-only; it does not implement,
deploy, merge, or ratify.

This document defines the pre-merge governance gates a Creator
Engine governed batch MUST satisfy before it may be merged onto the
canonical branch. It is the delivery-view companion to
[`./RELEASE_CANDIDATE_CHECKLIST.md`](./RELEASE_CANDIDATE_CHECKLIST.md)
(pre-RC evidence) and to
[`./DEPLOYMENT_APPROVAL_POLICY.md`](./DEPLOYMENT_APPROVAL_POLICY.md)
(post-merge deploy authority). Part of the **minimum repo-native
delivery control plane** and **not a Jira clone**. Layered onto, and
subordinate to, the Feature 001 substrate, the Feature 002 operating
model, and the existing delivery-view DoR / DoD / review-gate
documents. A fresh clone is sufficient to apply this checklist; no
external tracker credential or network state is required.

## a. Purpose

The merge-approval checklist makes one operational question
answerable from a fresh clone:

> Is Source's ratification of **this specific merge** of **this
> specific batch** onto **this specific canonical branch** recorded
> in a form that a fresh-clone reviewer can verify?

The checklist complements but does **not** amend the canonical
Definition of Done in
[`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md). DoD specifies
when a work item is `Done`; this checklist specifies the gates that
must be cleared **before** the merge mechanic that promotes the
batch from `Ratified` to `Done` per
`./BACKLOG.md` §a.

## b. Source-of-truth relationship

| Upstream source of truth | Role |
|---|---|
| Feature 001 FR-007 | Author / approver separation: the actor who authored the mutation MUST NOT be its ratifier. |
| Feature 001 FR-008 | Merge, deploy, organization / repository settings, governance, security, identity, attestation, and redaction mutations require explicit human Source ratification. |
| Feature 001 FR-016 | Ratification flow; required ratifier role per mutation class; valid ratification surfaces. |
| Feature 001 FR-017 / FR-018 | Agent-authored review text does not ratify privileged classes; a "go ahead" on a non-designated surface is not merge authorization. |
| Feature 001 FR-013 / FR-013a / FR-014 | Spec lifecycle and Definition of Done substrate contract. |
| Feature 002 FR-013 | Verifies-not-ratifies invariant: CI evidence is verification, never ratification. |
| [`./DEFINITION_OF_READY.md`](./DEFINITION_OF_READY.md) §b, §c | Readiness criteria; privileged-class rule. |
| [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §b, §c, §d | Done criteria; CI verifies / does not ratify; external tracker status cannot mark a repo item Done. |
| [`./REVIEW_GATE.md`](./REVIEW_GATE.md) §c–§m | Independent review evidence; standing invariants. |
| [`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md) §c–§l | Verifier-side scope audit consumed by this checklist. |
| [`./RELEASE_CANDIDATE_CHECKLIST.md`](./RELEASE_CANDIDATE_CHECKLIST.md) | Pre-merge release-candidate evidence package this checklist builds on. |
| [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b, §d | Ten post-merge completion-report fields and the post-merge update procedure. |
| `./BACKLOG.md` §a | Delivery-view status vocabulary including `Verified`, `Ratified`, and `Done`. |
| [`../../specs/sprint-0-minimum-viable-delivery-system/README.md`](../../specs/sprint-0-minimum-viable-delivery-system/README.md) §4 exit gate #11 | Sprint 0 exit gate: release / merge / deploy governance is documented. |
| [`../devops/RELEASE_AND_DEPLOYMENT_STRATEGY.md`](../devops/RELEASE_AND_DEPLOYMENT_STRATEGY.md) | Canonical release / deployment strategy this checklist layers onto. |
| [`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md) | Authority matrix and the surface-validity rule for ratification. |

Where this document and any upstream source disagree, the upstream
source controls until Source ratifies a correction.

## c. Pre-merge gates

A governed batch is **mergeable** on the delivery view only after
**every** gate below is cleared. Each gate is verifiable from
repository artifacts alone.

### c.1 Release-candidate evidence is complete

The batch satisfies every condition in
[`./RELEASE_CANDIDATE_CHECKLIST.md`](./RELEASE_CANDIDATE_CHECKLIST.md)
§c and carries the evidence fields in §d. A batch that has not
reached RC status MUST NOT be merged.

### c.2 Definition of Ready was satisfied at envelope authoring

The readiness gate in
[`./DEFINITION_OF_READY.md`](./DEFINITION_OF_READY.md) §b cleared
before consumption began: stable backlog id, named source of truth,
scope summary, allowed files and prohibited surfaces, anticipated
mutation class, dependencies at `Ratified` or `Done`, validation
plan, owner and ratifier role, external-tracker boundary, and stop
conditions. The privileged-class rule in
[`./DEFINITION_OF_READY.md`](./DEFINITION_OF_READY.md) §c was
applied when applicable: Source ratification of the envelope
preceded consumption.

### c.3 Definition of Done criteria are satisfied (where applicable pre-merge)

Every Done criterion in
[`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §b that is
verifiable pre-merge has been satisfied: implementation within
authorized scope (§b.1), validation evidence captured (§b.2),
scope audit completed (§b.3), independent review evidence recorded
when applicable (§b.4), Source ratification recorded for privileged
classes and (Phase 1) for non-privileged classes too (§b.5),
documented cleanup posture (§b.9). The post-merge-only criteria
(§b.6 PR / merge SHA, §b.7 ten-field report, §b.8 BACKLOG / KANBAN
refresh) are completed in the post-merge bookkeeping after the
merge mechanic, per
[`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §d.

### c.4 Source ratification is recorded for the merge itself

A repository-visible ratification record satisfying Feature 001
FR-016 and FR-020a names Source as the ratifier and authorizes the
merge of this batch onto the canonical branch. The record's signer
is distinct from the author of the mutation (Feature 001 FR-007).
The ratification surface is one the authority matrix in
[`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md)
§c designates as valid for the batch's dominant mutation class.

For privileged-class batches (any of `deploy`, `governance`,
`identity`, `security`, `attestation`, `redaction` per Feature 001
FR-008), Source ratification is mandatory. Author/approver
separation in Feature 001 FR-007 is non-negotiable: an envelope
authored by an agent or actor cannot be self-ratified by that same
agent or actor.

### c.5 Independent review evidence is in place (or Source-waived)

The review gate in
[`./REVIEW_GATE.md`](./REVIEW_GATE.md) §c is satisfied: independent
review evidence exists against the batch with a verdict drawn from
the four allowed values, or Source has explicitly waived the
requirement in the named batch's envelope. A
`no_blocking_findings` verdict is review evidence, not Source
ratification, per
[`./REVIEW_GATE.md`](./REVIEW_GATE.md) §m.1.

### c.6 Scope audit confirms no boundary or mechanics violation

The verifier-side audit in
[`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md) §c–§l
has been completed. The changed-file set is the union of the
envelope's allowed creates and directly needed allowed updates; no
prohibited surface was mutated; no staging, commit, push, PR,
merge, branch deletion, repo-settings, branch-protection, or hook
bypass was performed under the envelope's authorship; `git diff
--check` is clean; stale-language scans return the expected
results; markdown link / reference sanity holds; branch / worktree
isolation per
[`./WORKTREE_RUNTIME_PROTOCOL.md`](./WORKTREE_RUNTIME_PROTOCOL.md)
is preserved.

### c.7 The merge mechanic respects branch protection and prohibited actions

The merge mechanic itself MUST NOT bypass commit signing or
verification hooks, MUST NOT force-push to the canonical branch,
and MUST NOT delete other branches as a side effect. Any deviation
is itself a privileged action and requires its own Source
ratification per Feature 001 FR-008. The Slice C file-based branch
protection policy in `.github/BRANCH_PROTECTION_POLICY.md` is the
current repo-visible policy; live remote settings remain a
separate privileged future decision per
[`./README.md`](./README.md) §f and are NOT mutated by merge
approval under this checklist.

### c.8 Post-merge evidence expectations are agreed in advance

The post-merge completion report fields in
[`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b will be
filled out after the merge: merge identification, scope summary,
validation evidence, governance evidence, scope audit,
documentation impact, deferred work, readiness impact, immediate
next-task recommendation, and cleanup state.
`./BACKLOG.md` and
`./KANBAN.md` will be refreshed per
[`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §d.
Post-release evidence expectations are layered onto these fields
without amending them, per
[`./ROLLBACK_AND_POST_RELEASE_EVIDENCE.md`](./ROLLBACK_AND_POST_RELEASE_EVIDENCE.md)
§d.

## d. Source-ratification authority

The authority to approve a merge is **Source's**. Specifically:

1. For privileged-class batches per Feature 001 FR-008, Source is
   the sole ratifier and the ratifier MUST be human (FR-008,
   FR-017). No agent can ratify a merge for a privileged class.
2. For non-privileged classes (`docs`, `code`, `schema`), Source
   may have ratified delegation to a `ratifier` role; the
   delegation itself is a privileged `governance` decision
   requiring Source ratification per Feature 001 FR-008. Until
   such delegation is ratified, the operational default in v0.1
   Phase 1 is Source ratification of the canonical-branch
   integration per
   [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §b.5.
3. A reviewer (Codex or a future Feature 004 reviewer identity)
   MUST NOT be the merge ratifier of the same batch they reviewed
   ([`./REVIEW_GATE.md`](./REVIEW_GATE.md) §m.5).
4. The implementer who authored the mutation MUST NOT be the merge
   ratifier of that same mutation (Feature 001 FR-007).
5. Source ratification is recorded on a surface the authority
   matrix designates as valid for the batch's mutation class per
   [`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md)
   §c; a message on a non-designated surface is not merge
   authorization (Feature 001 FR-018).

## e. CI green is not Source ratification

**CI green is not Source ratification.** This restates the
load-bearing invariant from
[`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §c for the
merge gate:

1. CI green MAY be cited as **validation evidence** under §c.3
   when a CI workflow is wired for the batch's mutation class. CI
   red MUST block the merge.
2. CI green MUST NOT, by itself, satisfy §c.4. A passing CI run is
   mechanical verification; it is not Source ratification of the
   merge per Feature 001 FR-008.
3. A change to CI policy, branch protection, or `.github/`
   content is itself a privileged `governance` / `security` /
   `deploy`-class mutation per Feature 001 FR-008 and requires its
   own Source-ratified envelope.
4. An external tracker green check, an agent commentary verdict,
   or a "go ahead" message on a non-designated surface is not
   merge authorization (Feature 001 FR-018,
   [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §d).

## f. Author/approver separation

Feature 001 FR-007 prohibits the author of a mutation from being its
ratifier. For the merge gate this means:

1. The actor who authored the mutation (in v0.1 typically a visible
   Claude Code implementer under a Hermes / Nefarious controller)
   MUST NOT be the merge ratifier.
2. The reviewer who authored the independent review evidence MUST
   NOT be the merge ratifier of the same batch
   ([`./REVIEW_GATE.md`](./REVIEW_GATE.md) §m.5).
3. The independent verifier who ran the scope audit per
   [`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md)
   produces verification evidence; the auditor is not the merge
   ratifier of the same batch
   ([`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md)
   §k.4).
4. A self-merge by an implementer of their own batch is an
   authority conflict per Feature 002 FR-018 and triggers the
   halt / escalation path in
   [`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md).

## g. PR / merge evidence expectations

When the merge mechanic involves a PR (the v0.1 default once the
Slice C `.github/` baseline applies), the following PR / merge
evidence is captured into the post-merge report per
[`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b.1:

| Field | Description |
|---|---|
| PR identifier | The PR number visible in the canonical-branch merge commit subject (e.g., `#16`). In-flight PR numbers for unmerged work MUST NOT be cited in upstream artifacts. |
| Source branch | The feature branch consumed under the envelope. |
| Target branch | The canonical branch (`main`). |
| Merge commit SHA | The canonical-branch merge commit. |
| Merge type | The merge mechanic used (e.g., merge commit, squash merge), and whether it respected branch-protection policy. |
| Mutation class | The dominant mutation class touched, per [`../governance/MUTATION_CLASS_MODEL.md`](../governance/MUTATION_CLASS_MODEL.md). |
| Ratification reference | Repo-relative path or canonical-branch reference to the Source ratification record per Feature 001 FR-016 / FR-020a. |
| Review evidence reference | Repo-relative reference to the review-evidence artifact per [`./REVIEW_EVIDENCE_TEMPLATE.md`](./REVIEW_EVIDENCE_TEMPLATE.md), or an explicit Source-waiver note. |
| Scope-audit reference | Repo-relative reference to the scope-audit report-back per [`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md) §l, or an explicit "no audit applicable" note with Source rationale. |

Where the merge mechanic is not a PR (e.g., a fast-forward from a
Source-authored canonical-branch commit), the mechanic is named
explicitly and the SHA is captured per
[`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §b.6.

## h. Post-merge report expectations

After the merge mechanic completes, the post-merge completion
report per
[`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b is authored
using all ten fields without omission. The report:

1. Names the merge identification, scope summary, validation
   evidence, governance evidence, scope audit, documentation
   impact, deferred work, readiness impact, immediate next-task
   recommendation, and cleanup state.
2. Refreshes `./BACKLOG.md` and
   `./KANBAN.md` per
   [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §d so the
   merged item moves to `Done` and downstream items have their
   dependency states refreshed.
3. Confirms that no canonical-document or substrate surface was
   silently amended outside the envelope's allowed scope.
4. Confirms that the Feature 001 spec-status lifecycle on the
   affected spec(s) matches the delivery-view statuses applied
   (FR-027a), per
   [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §d.4.
5. Carries no instance-local facts per
   [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §e.

## i. Prohibited actions under this checklist

The following are explicitly **not** authorized by reaching merge
approval under this checklist:

1. No deploy. Deploy is governed by
   [`./DEPLOYMENT_APPROVAL_POLICY.md`](./DEPLOYMENT_APPROVAL_POLICY.md);
   no deployment targets currently exist.
2. No branch deletion as a merge side effect. Branch deletion is a
   separately ratifiable cleanup action per
   [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §b.9 and
   the default posture is retention pending explicit approval
   ([`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b.10).
3. No force-push to the canonical branch. Force-push is
   destructive remote action and remains prohibited absent a
   separate Source-ratified envelope per
   `./RISK_REGISTER.md` §c.8.
4. No live-repository-settings or branch-protection mutation as a
   side effect. The landed `.github/BRANCH_PROTECTION_POLICY.md`
   is file-based policy only; live remote settings remain a
   separate privileged future decision per
   [`./README.md`](./README.md) §f.
5. No hook bypass (no `--no-verify`, no signing bypass) absent
   explicit Source ratification, per
   [`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md)
   §e.7.

## j. Standing invariants

The following invariants apply to every merge-approval gate:

1. **This checklist authors policy.** It does not, and never
   becomes, a merge mechanic; it does not, and never becomes, a
   deploy mechanic; it does not, and never becomes, a
   substitute for Source ratification of the merge.
2. **Source ratification is the only authority that promotes a
   batch past `Verified` to `Ratified` and onward to `Done`** per
   `./BACKLOG.md` §a and
   [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §b.5.
3. **CI green is not Source ratification** (§e).
4. **Review evidence is not Source ratification** per
   [`./REVIEW_GATE.md`](./REVIEW_GATE.md) §m.1.
5. **Author/approver separation applies** per Feature 001 FR-007
   and §f above. An agent or actor MUST NOT ratify a merge of
   work they authored.
6. **Privileged mutation classes remain Source-only** per Feature
   001 FR-008 regardless of CI status, reviewer verdict, scope
   audit verdict, or external tracker status.
7. **A fresh clone is sufficient to evaluate every gate above.**
   Evidence that requires an external tracker credential, a chat
   surface, or a specific operator's environment is not merge
   evidence under this checklist.

## k. Acceptance posture for Slice F

This document satisfies the Slice F implementation envelope's
merge-approval-checklist requirements:

- Defines the pre-merge gates (§c.1–§c.8) that complement the
  Definition of Done and the review gate.
- Restates Source-ratification authority (§d) for both privileged
  and non-privileged classes under the current Phase 1 posture.
- Restates the Definition-of-Ready privileged-class rule (§c.2
  citing [`./DEFINITION_OF_READY.md`](./DEFINITION_OF_READY.md)
  §c), so an unratified privileged envelope cannot quietly slide
  into a merge gate.
- Names PR / merge evidence and post-merge report expectations
  (§g, §h), aligned with
  [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b.
- States explicitly that **CI green is not Source ratification**
  (§e) and that agent-authored review text / external tracker
  green / "go ahead" messages on non-designated surfaces do not
  authorize merge.
- States explicitly that **author/approver separation** prohibits
  an actor from ratifying their own merge (§f, Feature 001
  FR-007).
- Carries an explicit non-ratification statement throughout (§a,
  §e, §f, §j.1–§j.4) so reviewers cannot reasonably mistake
  merge-approval evidence for Source ratification or for a
  deploy authorization.
