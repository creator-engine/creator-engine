# Product Requirements Document — Creator Engine v0.1

**Status**: Canonical. Authored under Sprint 0 Execution Slice A.

**Scope**: Creator Engine v0.1 (governance substrate + operating model).

**Source-of-truth relationship**: REFERENCE. This document defers to
[`ROADMAP.md`](./ROADMAP.md) for sequencing detail and to
[`../architecture/agentic-sdlc-operating-model.md`](../architecture/agentic-sdlc-operating-model.md)
for SDLC mechanics. It restates neither the constitution nor any
Feature 001 contract.

## a. Product vision

Creator Engine is a repo-native agentic SDLC governance substrate. Its
purpose is to make agent-authored software work auditable, spec-driven,
identity-aware, mutation-class governed, verified by evidence, and
ratified by explicit authority rules. The v1.0 target is an end-to-end
governed agentic SDLC loop in which proposing work, implementing it,
verifying it, reviewing it, ratifying it, merging it, releasing it, and
recording post-release evidence are all governed mutations with a
durable repo-visible audit trail.

Creator Engine treats agents as productive proposers and humans as
ratifiers. It does not aspire to remove humans from governance; it
aspires to make agent productivity safe to scale by binding every
mutation to identity, mutation class, evidence, and a named ratifier.

## b. Target tenants and users

- **Tenants**: project owners and operators who want to govern
  agent-authored work in their own repositories. v0.1 ships repo-native
  artifacts only; tenants adopt Creator Engine by cloning a repository
  and reading its `git` history, not by standing up infrastructure.
- **Source**: the per-tenant project owner/operator who ratifies
  privileged mutations until a more formal authority registry exists.
- **Operators (Hermes/Nefarious role)**: the orchestrator/auditor who
  authors Assignment Envelopes, runs verification, drafts attestations,
  and enforces approval gates.
- **Implementation agents**: Claude Code is the operationally active
  implementer in v0.1. Codex is named as the independent reviewer with
  its governed identity record deferred to Feature 004.
- **Auditors**: humans or future tooling that read repository artifacts
  alone to reconstruct who proposed what, against which spec, with what
  evidence, ratified by whom.

## c. Problem statement

Agent-authored software work is currently auditable only by trust:
agents claim completion, humans accept the claim, and there is no
durable record that joins the claim to identity, evidence, and an
explicit ratifier. As agent productivity scales, ungoverned mutations
become indistinguishable from confabulated progress, "go ahead" in chat
becomes de facto merge authorization, and governance survives only as
human vigilance — which does not scale.

Creator Engine treats this as a contract problem rather than a tooling
problem: agents and humans need a shared, repo-visible substrate that
fixes identity, mutation class, permitted actions, verification
evidence, and ratifier *before* the agent acts and *records* them after
the agent acts.

## d. Value proposition

- **For tenants**: a single set of repository artifacts (schemas,
  contracts, validators, examples) that makes their agent-authored work
  reviewable months later from `git clone` alone.
- **For operators**: an explicit Assignment Envelope contract that
  bounds what an agent may do in a single invocation, and a conflict
  taxonomy that turns "the agents disagree" into a governed resolution
  path.
- **For source/ratifiers**: a clear, repo-visible separation between
  mutations agents may author and mutations only a human may ratify
  (the privileged mutation classes named in
  [`../governance/MUTATION_CLASS_MODEL.md`](../governance/MUTATION_CLASS_MODEL.md)).
- **For auditors**: a verifiable trail (attestation records, ratification
  records, redaction records, validator outputs) that reconstructs every
  governed mutation from repository content alone.
- **For Spec Kit users**: byte-identical compatibility — Creator Engine
  wraps Spec Kit with sidecar YAML; vanilla Spec Kit workflows keep
  working.

## e. Primary use cases

1. **Author a Creator-Engine-governed spec.** A tenant operator authors
   a Spec Kit `spec.md` plus the wrapper sidecar
   `spec.creator-engine.yml` declaring mutation class, scope, acceptance
   criteria, verification, ratification requirement, and identity
   policy reference.
2. **Dispatch a bounded agent batch via an Assignment Envelope.** Hermes
   drafts an Assignment Envelope from an approved task batch; Claude
   Code consumes the envelope; Source ratifies any privileged
   integration.
3. **Run repo-native validation.** From a fresh `git clone`, an
   operator or CI runs the validator to check spec wrapper conformance,
   identity-record completeness, mutation-class declaration presence,
   Definition of Ready / Definition of Done field requirements, and the
   tenant-identifier leak scan (command: `scan-no-limitless`), without
   external service calls.
4. **Ratify and record evidence.** Source ratifies a mutation; the
   ratification record and pre-merge attestation record are committed;
   on merge the attestation is finalized with the merge reference.
5. **Parallel feature work.** Multiple Hermes+Claude pairs work on
   different features simultaneously, each in an isolated worktree and
   branch under its own envelope, with canonical-branch integration
   serialized and Source-ratified.
6. **Audit weeks later.** A reviewer with `git clone` reconstructs who
   proposed what, against which spec, with which mutation class, with
   which evidence, and who ratified it.

## f. Explicit non-goals

Creator Engine v0.1 does not include and does not promise:

- **CI / GitHub Actions automation**: `.github/` workflows, branch
  protection rules applied to GitHub settings, PR templates, and CI
  validation checks are deferred to Feature 003 (GitHub CI Governance).
- **Independent review / QA agent governed identities**: the Codex
  reviewer identity record, the QA agent identity record, the security
  agent identity record, the review evidence schema, and the QA
  evidence schema are deferred to Feature 004 (Independent Review / QA
  Agent Evidence).
- **Dispatcher / worktree runtime**: an automated Hermes dispatcher,
  worktree lifecycle automation, sandboxing, and a safe parallel runtime
  are deferred to Feature 005 (Dispatch / Worktree / Sandbox Runtime).
  v0.1 specifies the manual protocol the future runtime must obey.
- **Release / deployment automation**: release records, deploy
  attestations, rollback evidence, GitHub environments, and
  Source-approved deploy gates are deferred to Feature 006
  (Release / Deployment Governance). v0.1 specifies the policy
  release/deploy must obey; it does not author any deploy automation.
- **Hosted SaaS or policy daemon**: per constitution Principle II,
  v0.1 ships only files inside a git repository.
- **Phase 2 autonomy expansion**: low-risk auto-merge, autonomous
  batch-pulling, and policy-bound automation are named as targets in
  the Phase 1 / Phase 2 boundary but are not implemented in v0.1.
- **Public or NDA-visible export workflows**: v0.1 defines the
  redaction-gate policy but executes no export.
- **Drift detection, dashboards, multi-tenant SaaS behavior**: per
  constitution Principle XI (YAGNI for v0.1).
- **Tenant-specific assumptions in substrate artifacts**: per
  constitution Principle IX, the substrate remains project-agnostic;
  tenant fixtures live under `tenants/<tenant>/`.

## g. Technology-agnostic success metrics

Creator Engine measures success in terms of auditable mutations and
ratifiable batches, not in terms of implementation throughput.

- **Auditability from `git clone` alone**: a reviewer with the
  repository contents can reconstruct, for any governed mutation, the
  five v0.1 governance answers (identity, spec, ratifier, evidence,
  attestation) without consulting any external system.
- **Ratifiable batch coverage**: every executable agent batch is bound
  to an approved Assignment Envelope declaring mutation classes,
  prohibited surfaces, required validation, and stop conditions; no
  governed batch executes outside an envelope.
- **Author/approver separation enforcement**: no mutation is accepted
  whose author equals its ratifier; no envelope is consumed whose
  author equals its consumer.
- **Privileged-class ratification integrity**: 100% of privileged
  mutation classes (`deploy`, `governance`, `identity`, `security`,
  `attestation`, `redaction`) are Source-ratified; no agent-authored
  review text is recorded as ratification for these classes.
- **Repo-native completeness**: every contract, schema, validator,
  example, and attestation record is reachable from the repository
  with no hosted dependency.
- **Spec Kit compatibility preserved**: vanilla `spec.md` / `plan.md` /
  `tasks.md` files remain byte-identical to vanilla Spec Kit; Creator
  Engine governance metadata lives only in adjacent sidecar files.

## h. Version scope summaries

Cross-linked to [`ROADMAP.md`](./ROADMAP.md), which carries the
authoritative per-feature scope and deferral rationale.

- **v0.1 — governance substrate + operating model**. Feature 001 ships
  the law (identity, mutation-class taxonomy, authority matrix,
  attestation record format, ratification flow, redaction gate policy,
  validator, examples, dogfood tenant fixture). Feature 002 ships
  the civilization (SDLC state machine, Assignment Envelope spec,
  `/speckit-implement` policy, actor/tool ownership matrix,
  parallel-agent development model, conflict taxonomy, source-of-truth
  hierarchy, the canonical document set, Phase 1 / Phase 2 boundary,
  automation deferrals).
- **v0.2 — GitHub CI governance**. Feature 003 wires `.github/`
  workflows, baseline CI checks, PR templates, branch protection policy,
  and the CI-evidence linkage to SDLC transition T17 specified by
  Feature 002. CI verifies; CI never ratifies.
- **v0.3 — independent review / QA agent evidence**. Feature 004
  instantiates the Codex reviewer identity record, the QA agent
  identity record, the security agent identity record, and the review /
  QA / security evidence schemas. Review evidence remains distinct from
  ratification.
- **v0.4 — dispatch / worktree / sandbox runtime**. Feature 005
  implements the Hermes dispatcher, worktree lifecycle automation,
  sandboxing, and safe parallel runtime — bound by the manual protocol
  Feature 002 specifies. Feature 005 must preserve one-driver-per-
  worktree and the conflict taxonomy.
- **v0.5 — release / deployment governance**. Feature 006 instantiates
  the release agent identity record, release records, deploy
  attestations, rollback evidence, GitHub environments, and
  Source-approved deploy gates. The `deploy` mutation class remains
  Source-only.
- **v1.0 — end-to-end governed agentic SDLC loop**. The integration
  target: Features 001 through 006 compose into a single governed
  loop that runs from `Idea/Intent` through `Post-release Evidence
  Recorded` with every privileged gate human-ratified and every
  non-privileged gate eligible for ratified Phase 2 expansion.

## Acceptance posture for this document

This PRD satisfies Feature 002 Canonical Document Specification #2:
every required section (a–h) is non-empty; non-goals enumerate the
Feature 003 / 004 / 005 / 006 deferrals; success metrics are framed in
terms of auditable mutations and ratifiable batches rather than
implementation throughput; version-scope summaries cross-link to
ROADMAP.md without redefining its content.
