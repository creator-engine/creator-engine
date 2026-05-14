# Release / Deploy Governance (Slice F index)

**Status**: Sprint 0 Slice F landed policy. Authored via PR #16 /
`cb7f94a`; delivery-state reconciliation landed via PR #17 /
`5be005b`. This document remains policy-only; it does not implement,
deploy, merge, or ratify.

This document is the **index / front door** for the four Sprint 0
Slice F content documents that author Creator Engine v0.1's
release, merge, deployment, and post-release governance policy. It
binds the four siblings into a single navigational entry point and
names the boundary between Slice F policy authoring and Feature
006 execution / identities. Part of the **minimum repo-native
delivery control plane** and **not a Jira clone**. A fresh clone
is sufficient to walk this index; no external tracker credential
or network state is required.

## a. Purpose

The index makes one operational question answerable from a fresh
clone:

> Where, in this repository, is the policy that governs how
> Creator Engine v0.1 promotes a batch to release-candidate
> status, approves its merge, approves any future deploy, and
> handles rollback / post-release evidence — and how is that
> policy bounded against Feature 006 execution / identity work?

The four content documents bound by this index answer that
question collectively. Each is independently usable; this index
serves navigation and boundary statement only.

## b. The four bound content documents

| Document | Role |
|---|---|
| [`./RELEASE_CANDIDATE_CHECKLIST.md`](./RELEASE_CANDIDATE_CHECKLIST.md) | Defines what promotes an in-progress batch to release-candidate status: validator pass, review-gate state per [`./REVIEW_GATE.md`](./REVIEW_GATE.md), scope audit per [`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md), Source ratification record per Feature 001 FR-016, and the explicit non-ratification statement that RC status does not authorize merge or deploy. |
| [`./MERGE_APPROVAL_CHECKLIST.md`](./MERGE_APPROVAL_CHECKLIST.md) | Defines the pre-merge gates complementing the Definition of Done and the review gate. Restates Source-ratification authority, the Definition-of-Ready privileged-class rule, PR / merge evidence, and post-merge report expectations. Explicitly: CI green is not Source ratification, and author / approver separation per Feature 001 FR-007 prohibits an actor from ratifying their own merge. |
| [`./DEPLOYMENT_APPROVAL_POLICY.md`](./DEPLOYMENT_APPROVAL_POLICY.md) | Names `deploy` as a Feature 001 FR-008 privileged mutation class with **Source-only** ratifier. States the explicit deploy-mutation ratification rule: **no agent may deploy without Source-ratified authority**. States that no deployment targets or environments currently exist. Defers execution-side concerns to Feature 006. Carries an explicit non-ratification statement for any CI / review / scope-audit / external-tracker verdict touching deploy. |
| [`./ROLLBACK_AND_POST_RELEASE_EVIDENCE.md`](./ROLLBACK_AND_POST_RELEASE_EVIDENCE.md) | Defines rollback decision criteria: who decides, on what evidence, under what governance authority. Layers post-release evidence onto the ten post-merge fields in [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b **without amending them**. Names the defect-discovered-post-merge interaction with the Definition-of-Done lifecycle. Defers automated rollback to Feature 006. |

The four siblings cross-reference each other; this index does not
duplicate their content.

## c. Source-of-truth relationship

| Upstream source of truth | Role |
|---|---|
| Feature 001 FR-006 / FR-007 / FR-008 / FR-016 / FR-017 / FR-018 / FR-020a | Substrate contract on mutation classes, author / approver separation, privileged-class ratification, ratification flow, agent-text-is-not-ratification, surface-validity, and ratification record storage. |
| Feature 002 FR-013 | Verifies-not-ratifies invariant. |
| [`./README.md`](./README.md) | Delivery control plane purpose, source-of-truth relationship, and tracker boundary. |
| [`./BACKLOG.md`](./BACKLOG.md) §a, §c.6 | Delivery-view status vocabulary; Slice F row. |
| [`./KANBAN.md`](./KANBAN.md) | Current Kanban view of the Slice F row. |
| [`./DEPENDENCIES.md`](./DEPENDENCIES.md) §b, §d.4, §h | Sprint 0 dependency chain (A → B → C → D → E → F); Feature 006 → Slice F edge; privileged-dependency rule. |
| [`./DEFINITION_OF_READY.md`](./DEFINITION_OF_READY.md) §b, §c | Readiness criteria; privileged-class rule. |
| [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §b, §c, §d, §e | Done criteria; CI verifies / does not ratify; external tracker status cannot mark `Done`; reopen rule. |
| [`./REVIEW_GATE.md`](./REVIEW_GATE.md) §c–§m | Review-gate semantics and standing invariants. |
| [`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md) §c–§l | Verifier-side scope audit. |
| [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b, §d, §e | Ten post-merge fields; post-merge update procedure; prohibited content. |
| [`./RISK_REGISTER.md`](./RISK_REGISTER.md) §c.3, §c.7, §c.8 | Risks bearing on Slice F policy. |
| [`../devops/RELEASE_AND_DEPLOYMENT_STRATEGY.md`](../devops/RELEASE_AND_DEPLOYMENT_STRATEGY.md) | Canonical release / deployment strategy this slice's policy layers onto. |
| [`../product/ROADMAP.md`](../product/ROADMAP.md) §f | Feature 006 scope (release / deployment governance) and deferral rationale. |
| [`../../specs/sprint-0-minimum-viable-delivery-system/README.md`](../../specs/sprint-0-minimum-viable-delivery-system/README.md) §4 exit gate #11; §5 Slice F | Sprint 0 exit gate and Slice F acceptance criteria. |

Where this document and any upstream source disagree, the upstream
source controls until Source ratifies a correction.

## d. Boundary — Sprint 0 Slice F vs. Feature 006

Slice F authors **policy** for release, merge, deployment, and
post-release evidence. Feature 006 implements the **execution
surface** and instantiates the **identities** that that policy
governs. The boundary is fixed:

| Surface | Slice F (this slice) | Feature 006 (deferred) |
|---|---|---|
| Release-candidate criteria | Authored in [`./RELEASE_CANDIDATE_CHECKLIST.md`](./RELEASE_CANDIDATE_CHECKLIST.md). | Not authored. |
| Merge-approval gates | Authored in [`./MERGE_APPROVAL_CHECKLIST.md`](./MERGE_APPROVAL_CHECKLIST.md). | Not authored. |
| Deploy-approval policy | Authored in [`./DEPLOYMENT_APPROVAL_POLICY.md`](./DEPLOYMENT_APPROVAL_POLICY.md). | Not authored. |
| Rollback policy | Authored in [`./ROLLBACK_AND_POST_RELEASE_EVIDENCE.md`](./ROLLBACK_AND_POST_RELEASE_EVIDENCE.md). | Not authored. |
| Release agent identity | Not authored (the Slice D pattern in [`./REVIEWER_IDENTITY_REQUIREMENTS.md`](./REVIEWER_IDENTITY_REQUIREMENTS.md) is generic and is not a release agent). | Instantiated under a separate Source-ratified privileged envelope. |
| Release records | Markdown policy only. | Machine-readable release records, deploy attestations, rollback records. |
| Deploy automation | Not authored. | Authored. |
| GitHub environments | Not authored, not mutated. | Authored under a separate privileged envelope; live GitHub-settings mutation remains its own privileged decision. |
| Source-approved deploy gates for SDLC transitions T22–T24 | Named as out of scope. | Instantiated as automated checks. |
| Rollback automation | Deferred. | Authored. |
| Live-source-host mutations (deploy keys, environment secrets, OIDC trust, etc.) | Not authored, not mutated. | Authored. |

Slice F landing does **not**, by itself, authorize any Feature
006 work. Per
[`./DEPENDENCIES.md`](./DEPENDENCIES.md) §h, clearing the Slice F
→ Feature 006 predecessor edge is not authorization to consume
Feature 006; a separate Source-ratified privileged envelope is
required.

## e. No deployment targets / environments currently exist

Restating the load-bearing fact from
[`./DEPLOYMENT_APPROVAL_POLICY.md`](./DEPLOYMENT_APPROVAL_POLICY.md)
§e for this index:

> **Creator Engine v0.1 has no deployment targets and no
> deployment environments in this repository.**

Consequently:

1. No GitHub environments are defined.
2. No deploy-automation workflow exists. The Slice C `.github/`
   baseline is file-based governance only and does not deploy.
3. No release agent identity is instantiated.
4. No tenant overlay binds Creator Engine v0.1 to a production
   or staging environment.
5. No `deploy`-class mutation has been Source-ratified to date.

The Slice F policy is non-vacuous: it applies from the moment any
deployment target is first declared, before any environment is
created, and constrains how that first target must be brought
under Source-ratified authority.

## f. What this slice does NOT author or mutate

Explicit boundary statement: **this slice does not author or
mutate any of the following surfaces, and the four Slice F
content documents do not, by themselves, authorize any agent or
human to mutate them:**

1. **`.github/`** — no workflow, PR template, branch-protection
   policy file, CODEOWNERS, or other `.github/` content is
   authored, modified, or added under Slice F. The Slice C
   `.github/` baseline already on the canonical branch
   (`validate.yml`, `pull_request_template.md`,
   `BRANCH_PROTECTION_POLICY.md`) is unchanged. Any extension of
   that baseline is Feature 003 surface under a separately
   ratified privileged envelope per
   [`./DEPENDENCIES.md`](./DEPENDENCIES.md) §d.1.
2. **`CODEOWNERS`** — no `CODEOWNERS` file exists in the
   repository and no `CODEOWNERS` file is authored, modified, or
   added under Slice F.
3. **Live source-host settings on the remote repository** — no
   live GitHub repository settings (visibility, default branch,
   merge settings, repository topics, etc.) are mutated under
   Slice F. Live settings remain a separate privileged future
   decision per
   [`./README.md`](./README.md) §f and
   [`./BACKLOG.md`](./BACKLOG.md) §e.3.
4. **Branch protection (live)** — no live branch-protection
   rule on the remote repository is created, modified, or
   removed under Slice F. The landed
   `.github/BRANCH_PROTECTION_POLICY.md` is file-based policy
   only.
5. **Environments** — no GitHub environments are created,
   modified, or removed under Slice F. None exist (§e above).
6. **Deploy automation** — no deploy workflow, release
   pipeline, signing key, signing job, deploy job, rollback job,
   or environment-secret mutation is authored under Slice F.
   Deploy automation is Feature 006 surface per
   [`../product/ROADMAP.md`](../product/ROADMAP.md) §f.
7. **`specs/`, `schemas/`, `validators/`, `templates/`,
   `examples/`, `tenants/`** — none of these substrate surfaces
   is authored or mutated under Slice F.
8. **`docs/contracts/`, `docs/product/`, `docs/architecture/`,
   `docs/governance/`, `docs/quality/`, `docs/devops/`,
   `docs/security/`** — none of the canonical-document subtrees
   is authored or mutated under Slice F. Slice F's docs live
   exclusively under `docs/delivery/` per the envelope.

A diff under Slice F that includes any of the above is a
scope-audit failure per
[`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md) §c–§d
and is either reverted under the envelope's authorship or
reclassified under a separate Source-ratified envelope.

## g. Cross-document cross-references at a glance

The four content docs share a load-bearing set of references for
quick navigation:

| Concept | Authored in | Restated / cross-referenced in |
|---|---|---|
| What promotes a batch to RC status | [`./RELEASE_CANDIDATE_CHECKLIST.md`](./RELEASE_CANDIDATE_CHECKLIST.md) §c | [`./MERGE_APPROVAL_CHECKLIST.md`](./MERGE_APPROVAL_CHECKLIST.md) §c.1; this index §b. |
| Source-ratification authority for merge | [`./MERGE_APPROVAL_CHECKLIST.md`](./MERGE_APPROVAL_CHECKLIST.md) §d | This index §b; [`./DEPLOYMENT_APPROVAL_POLICY.md`](./DEPLOYMENT_APPROVAL_POLICY.md) §g.5. |
| `deploy` is Source-only per FR-008 | [`./DEPLOYMENT_APPROVAL_POLICY.md`](./DEPLOYMENT_APPROVAL_POLICY.md) §c, §d | [`./RELEASE_CANDIDATE_CHECKLIST.md`](./RELEASE_CANDIDATE_CHECKLIST.md) §e.2, §f.6; [`./MERGE_APPROVAL_CHECKLIST.md`](./MERGE_APPROVAL_CHECKLIST.md) §i.1; [`./ROLLBACK_AND_POST_RELEASE_EVIDENCE.md`](./ROLLBACK_AND_POST_RELEASE_EVIDENCE.md) §c.4. |
| No deployment targets currently exist | [`./DEPLOYMENT_APPROVAL_POLICY.md`](./DEPLOYMENT_APPROVAL_POLICY.md) §e | This index §e; [`./ROLLBACK_AND_POST_RELEASE_EVIDENCE.md`](./ROLLBACK_AND_POST_RELEASE_EVIDENCE.md) §c.4, §f. |
| Rollback decision criteria | [`./ROLLBACK_AND_POST_RELEASE_EVIDENCE.md`](./ROLLBACK_AND_POST_RELEASE_EVIDENCE.md) §c | This index §b; [`./MERGE_APPROVAL_CHECKLIST.md`](./MERGE_APPROVAL_CHECKLIST.md) §i (cleanup actions). |
| Post-release evidence layered onto NEXT_TASK_PROTOCOL §b | [`./ROLLBACK_AND_POST_RELEASE_EVIDENCE.md`](./ROLLBACK_AND_POST_RELEASE_EVIDENCE.md) §d | [`./MERGE_APPROVAL_CHECKLIST.md`](./MERGE_APPROVAL_CHECKLIST.md) §h. |
| Author / approver separation per FR-007 | Throughout all four content docs | This index §b; Feature 001 FR-007. |
| CI verifies, CI does not ratify | [`./MERGE_APPROVAL_CHECKLIST.md`](./MERGE_APPROVAL_CHECKLIST.md) §e | [`./RELEASE_CANDIDATE_CHECKLIST.md`](./RELEASE_CANDIDATE_CHECKLIST.md) §f.4; [`./DEPLOYMENT_APPROVAL_POLICY.md`](./DEPLOYMENT_APPROVAL_POLICY.md) §g.1; [`./ROLLBACK_AND_POST_RELEASE_EVIDENCE.md`](./ROLLBACK_AND_POST_RELEASE_EVIDENCE.md) §g.4. |

## h. Standing invariants

The following invariants apply to every reading and use of this
index and of its four bound content documents:

1. **This slice documents policy.** It does not, and never
   becomes, a merge mechanic, a deploy mechanic, or a rollback
   mechanic. It does not, and never becomes, Source ratification
   of any mutation.
2. **`deploy` is Source-only per Feature 001 FR-008.** No agent
   may deploy without Source-ratified authority
   ([`./DEPLOYMENT_APPROVAL_POLICY.md`](./DEPLOYMENT_APPROVAL_POLICY.md)
   §d).
3. **No deployment targets currently exist** (§e).
4. **CI verifies; CI does not ratify** for release-candidate,
   merge, deploy, and rollback decisions alike (Feature 002
   FR-013).
5. **Review evidence is not Source ratification**
   ([`./REVIEW_GATE.md`](./REVIEW_GATE.md) §m.1).
6. **Author / approver separation applies** to release-candidate
   evidence, merge approval, deploy approval, and rollback
   ratification (Feature 001 FR-007).
7. **This slice does not author or mutate `.github/`,
   `CODEOWNERS`, environments, branch protection, or deploy
   automation** (§f). Those surfaces remain Feature 003 /
   Feature 006 / separately-ratified scope.
8. **A fresh clone is sufficient to navigate, read, and apply
   this index and its four bound content documents.** No
   external tracker credential or network state is required.

## i. Acceptance posture for Slice F

This document satisfies the Slice F implementation envelope's
index-document requirements:

- Acts as the **front door** for the four sibling content
  documents (§b), without duplicating their content.
- Names the **boundary** between Sprint 0 Slice F policy
  authoring and Feature 006 execution / identities (§d) per
  [`../product/ROADMAP.md`](../product/ROADMAP.md) §f and
  [`./DEPENDENCIES.md`](./DEPENDENCIES.md) §d.4.
- Restates the **no-deployment-targets** fact (§e), aligned with
  [`./DEPLOYMENT_APPROVAL_POLICY.md`](./DEPLOYMENT_APPROVAL_POLICY.md)
  §e.
- States explicitly that **this slice does not author or mutate
  `.github/`, `CODEOWNERS`, environments, branch protection, or
  deploy automation** (§f).
- Carries an explicit non-ratification statement throughout (§a,
  §d, §g, §h.1, §h.4, §h.5) so reviewers cannot reasonably
  mistake any Slice F document, validation pass, or review
  verdict for Source ratification of a merge, deploy, or
  rollback.
