# Deployment Approval Policy

**Status**: Sprint 0 Slice F landed policy. Authored via PR #16 /
`cb7f94a`; delivery-state reconciliation landed via PR #17 /
`5be005b`. This document remains policy-only; it does not implement,
deploy, merge, or ratify.

This document is the deployment-approval policy for Creator Engine
v0.1. It names `deploy` as a Feature 001 FR-008 privileged mutation
class with **Source-only ratification**, states the explicit
deploy-mutation ratification rule, and records that **no
deployment targets or environments currently exist** in this
repository. Execution-side concerns (release agent identity,
deploy attestations, rollback automation, GitHub environments,
Source-approved deploy gates for SDLC transitions T22–T24) are
deferred to Feature 006 per
[`../product/ROADMAP.md`](../product/ROADMAP.md) §f. Part of the
**minimum repo-native delivery control plane** and **not a Jira
clone**. A fresh clone is sufficient to apply this policy; no
external tracker credential or network state is required.

## a. Purpose

The deployment-approval policy makes one operational fact
answerable from a fresh clone:

> Who can authorize a deploy mutation in Creator Engine v0.1, and
> what evidence is required for that authorization to be
> recognized as valid?

The answer in v0.1 is **Source-only**, recorded per Feature 001
FR-016, on a surface the authority matrix designates as valid for
the `deploy` mutation class. No agent, no CI workflow, no
reviewer, and no external tracker check can authorize a deploy.
The policy holds regardless of whether deploy automation is wired
or not.

This document **authors policy**; it does not implement, deploy,
merge, or ratify any mutation. Deploy execution mechanics (release
records, deploy attestations, rollback evidence, GitHub
environments, dispatcher behaviour) are Feature 006 surface and
remain deferred until Feature 006 is itself Source-ratified per
`./DEPENDENCIES.md` §d.4.

## b. Source-of-truth relationship

| Upstream source of truth | Role |
|---|---|
| Feature 001 FR-006 | Mutation-class taxonomy (the nine baseline classes including `deploy`). |
| Feature 001 FR-008 | `deploy` is a privileged mutation class requiring explicit human Source ratification. |
| Feature 001 FR-016 | Ratification flow; required ratifier role per mutation class; valid ratification surfaces. |
| Feature 001 FR-017 / FR-018 | Agent-authored review text does not ratify privileged classes; a "go ahead" on a non-designated surface is not deploy authorization. |
| Feature 002 FR-013 | Verifies-not-ratifies invariant: CI evidence is verification, never ratification. |
| [`./DEFINITION_OF_READY.md`](./DEFINITION_OF_READY.md) §c | Privileged-class rule: Source ratification before implementation; no shortcuts. |
| [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §b.5, §c | Source ratification record for privileged classes; CI verifies but does not ratify. |
| [`./REVIEW_GATE.md`](./REVIEW_GATE.md) §f, §m.1, §m.2 | Privileged classes remain Source-ratified regardless of reviewer verdict; review evidence is not Source ratification. |
| `./DEPENDENCIES.md` §d.4, §h | Feature 006 depends on Slice F; privileged dependencies require ratification requests, not implementation shortcuts. |
| `./RISK_REGISTER.md` §c.3, §c.7 | Risks R-003 (skipping Source ratification because CI / review passed) and R-007 (privileged classes implemented without ratification). |
| Sibling Slice F docs ([`./RELEASE_CANDIDATE_CHECKLIST.md`](./RELEASE_CANDIDATE_CHECKLIST.md), [`./MERGE_APPROVAL_CHECKLIST.md`](./MERGE_APPROVAL_CHECKLIST.md), [`./ROLLBACK_AND_POST_RELEASE_EVIDENCE.md`](./ROLLBACK_AND_POST_RELEASE_EVIDENCE.md), [`./RELEASE_DEPLOY_GOVERNANCE.md`](./RELEASE_DEPLOY_GOVERNANCE.md)) | Slice F policy envelope; this document is one of four content docs bound by the index. |
| [`../devops/RELEASE_AND_DEPLOYMENT_STRATEGY.md`](../devops/RELEASE_AND_DEPLOYMENT_STRATEGY.md) | Canonical release / deployment strategy this policy layers onto. |
| [`../governance/MUTATION_CLASS_MODEL.md`](../governance/MUTATION_CLASS_MODEL.md) | Authoritative `deploy` mutation-class definition; canonical surfaces that count as `deploy` even when the diff looks docs-only. |
| [`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md) | Authority matrix; surface-validity rule for ratification. |
| [`../product/ROADMAP.md`](../product/ROADMAP.md) §f | Feature 006 scope and deferral rationale. |
| [`../../specs/sprint-0-minimum-viable-delivery-system/README.md`](../../specs/sprint-0-minimum-viable-delivery-system/README.md) §4 exit gate #11; §5 Slice F acceptance | Sprint 0 exit gate and Slice F acceptance criteria. |

Where this document and any upstream source disagree, the upstream
source controls until Source ratifies a correction.

## c. `deploy` is an FR-008 privileged class with Source-only ratifier

Per Feature 001 FR-008, the substrate states that mutation classes
touching merge, **deploy**, publish / export, credential or token
issuance / revocation, organization / tenant / repository
settings, governance, security, identity, attestation-gate
weakening, or redaction-gate weakening require **explicit human
(not agent) ratification**.

For Creator Engine v0.1:

1. The ratifier of any `deploy` mutation is **Source**. There is
   no Source-delegated `ratifier` for `deploy` in v0.1 and none
   may be introduced without an explicit Source-ratified
   `governance` envelope that amends the authority matrix.
2. The ratifier MUST be human (Feature 001 FR-008, FR-017). No
   agent may ratify a `deploy` mutation regardless of the agent's
   capability, review verdict, or commentary.
3. The ratification is recorded per Feature 001 FR-016 / FR-020a:
   a YAML record, one record per file, under the tenant-declared
   `ratification_storage_path`, naming the mutation id and the
   ratifying actor.
4. The ratification surface MUST be one the authority matrix in
   [`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md)
   §c designates as valid for the `deploy` class. A message on a
   non-designated surface is not deploy authorization (Feature
   001 FR-018).
5. Author / approver separation applies: the actor who authored
   the `deploy` mutation MUST NOT be its ratifier (Feature 001
   FR-007).

## d. Explicit deploy-mutation ratification rule

> **No agent may deploy without Source-ratified authority.**

The rule applies in the strongest form: no agent (including any
implementer agent, reviewer agent, QA agent, dispatcher, or
future release agent) MAY perform a `deploy`-class mutation
without:

1. a Source-ratified envelope per Feature 001 FR-016 that names
   the `deploy` mutation class in its `allowed_mutation_classes`
   and the target of the deploy in its allowed-paths /
   allowed-actions list; and
2. a separate ratification record for the specific deploy event
   per Feature 001 FR-016 / FR-020a, with Source as ratifier, on
   a surface the authority matrix designates as valid.

A passing CI workflow, a `no_blocking_findings` reviewer verdict,
an external tracker green check, a successful release-candidate
gate per
[`./RELEASE_CANDIDATE_CHECKLIST.md`](./RELEASE_CANDIDATE_CHECKLIST.md),
a merge approval per
[`./MERGE_APPROVAL_CHECKLIST.md`](./MERGE_APPROVAL_CHECKLIST.md),
or any combination of the above MUST NOT substitute for
Source-ratified deploy authority. Each authorizes its own narrow
action and no other.

The rule also applies in reverse: a Source ratification of a
non-`deploy` envelope (e.g., a `governance` policy-authoring
envelope such as the one authoring this very document) MUST NOT
be read as authority to deploy. Authority is class-scoped per
Feature 001 FR-008.

## e. No deployment targets or environments currently exist

**Creator Engine v0.1 has no deployment targets and no
deployment environments in this repository.** Specifically:

1. No GitHub environments are defined in this repository.
2. No deploy-automation workflow exists. The Slice C `.github/`
   baseline (`validate.yml`, `pull_request_template.md`,
   `BRANCH_PROTECTION_POLICY.md`) is the file-based governance
   baseline only; it does not deploy.
3. No release agent identity record has been instantiated. The
   reviewer-identity **pattern** in
   [`./REVIEWER_IDENTITY_REQUIREMENTS.md`](./REVIEWER_IDENTITY_REQUIREMENTS.md)
   is generic and is not a release agent.
4. No tenant overlay binds Creator Engine v0.1 to a production,
   staging, or other named environment. Tenant overlays remain
   under separate tenant-local fixtures (FR-001) and are out of
   scope for Slice F.
5. No `deploy`-class mutation has been Source-ratified in v0.1 to
   date; the privileged class is named in the substrate (Feature
   001 FR-008) but no concrete deploy has been performed.

Consequently, the deploy-approval policy in this document is
**non-vacuous policy authoring** that constrains any future deploy
mutation from the moment a deployment target is first declared.
The policy applies **before** any environment is created; it does
not wait for Feature 006 to exist.

## f. Execution-side concerns are deferred to Feature 006

The following are explicitly **Feature 006** scope and are not
authored, mutated, or implemented under Slice F:

1. Release agent identity record (instantiated, not the generic
   reviewer pattern).
2. Release records, deploy attestations, and rollback evidence
   records as machine-readable artifacts beyond the markdown
   policy authored here and in sibling Slice F docs.
3. GitHub environments, environment protection rules, and any
   live-source-host environment mutation.
4. Source-approved deploy gates for SDLC transitions T22–T24 as
   automated checks.
5. Any deploy-automation workflow, signing key, release pipeline,
   or rollback automation.
6. Any live-source-host mutation related to deploys (environment
   secrets, deploy keys, OIDC trust, release tags pushed by an
   automated mechanism, etc.).

The Feature 006 → Slice F dependency in
`./DEPENDENCIES.md` §d.4 names this
boundary: Slice F authors the policy outline; Feature 006
instantiates the execution surface under its own Source-ratified
privileged envelope.

The `deploy` class remains Source-only per Feature 001 FR-008
regardless of any Feature 006 automation. Feature 006 implements
the execution surface; ratification of every deploy remains
Source's. Automation does not displace the human ratifier.

## g. CI / review verdicts touching deploy are not Source ratification

The verifies-not-ratifies invariant
([`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §c, Feature
002 FR-013) applies specifically to `deploy` evidence:

1. A CI workflow that runs deploy-adjacent checks (build, smoke,
   lint, validator, contract tests) produces **validation
   evidence** only. A green check is not a deploy authorization.
2. A reviewer verdict (`no_blocking_findings` or otherwise) on a
   batch that touches `deploy`-class paths is **review
   evidence** only; the reviewer cannot waive the FR-008
   privileged gate
   ([`./REVIEW_GATE.md`](./REVIEW_GATE.md) §f, §m.2).
3. An external tracker green check, a chat surface "ship it"
   message, or a passing automation hook is not deploy
   authorization (Feature 001 FR-018).
4. A successful scope-audit verdict per
   [`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md)
   §k is verification evidence and not deploy authorization.
5. A merge approval per
   [`./MERGE_APPROVAL_CHECKLIST.md`](./MERGE_APPROVAL_CHECKLIST.md)
   authorizes the merge of a batch onto the canonical branch; it
   does NOT, by itself, authorize any subsequent deploy. The
   deploy authorization is a separate Source ratification per
   §c.3 and §d.

## h. Standing invariants

The following invariants apply to every potential `deploy`
mutation in Creator Engine v0.1:

1. **`deploy` is Source-only per Feature 001 FR-008.** No agent,
   no CI, no reviewer, and no external tracker check can
   authorize a deploy.
2. **No deployment targets currently exist** (§e); the policy
   constrains the first deploy from before it is conceived.
3. **No agent may deploy without Source-ratified authority** (§d).
4. **CI verifies; CI does not ratify** (§g.1, Feature 002 FR-013).
5. **Review evidence is not Source ratification** (§g.2,
   [`./REVIEW_GATE.md`](./REVIEW_GATE.md) §m.1).
6. **Author / approver separation applies.** The actor who would
   author a deploy MUST NOT be its ratifier (Feature 001 FR-007).
7. **This slice documents policy; this slice does not deploy and
   does not implement deploy automation.** Execution is Feature
   006 surface (§f).
8. **A fresh clone is sufficient to read and apply this policy.**
   No external tracker credential or network state is required.

## i. Acceptance posture for Slice F

This document satisfies the Slice F implementation envelope's
deployment-approval-policy requirements:

- Names `deploy` as a Feature 001 FR-008 privileged mutation
  class with **Source-only ratifier** (§c).
- States the explicit deploy-mutation ratification rule: **no
  agent may deploy without Source-ratified authority** (§d).
- States explicitly that **no deployment targets or environments
  currently exist** in this repository (§e).
- Defers execution-side concerns (release agent identity, deploy
  attestations, rollback automation, GitHub environments, deploy
  gates) to Feature 006 (§f) per
  [`../product/ROADMAP.md`](../product/ROADMAP.md) §f and
  `./DEPENDENCIES.md` §d.4.
- Carries an explicit non-ratification statement for any CI /
  review / scope-audit / external-tracker verdict touching deploy
  (§g, §h.4–§h.5).
- Carries an explicit non-ratification statement throughout
  (§a, §c, §d, §g, §h) so reviewers cannot reasonably mistake any
  policy artifact, validation pass, or review verdict for deploy
  authorization.
