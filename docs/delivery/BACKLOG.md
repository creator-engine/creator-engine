# Creator Engine Backlog

**Status**: Sprint 0 Slices B, C, D, E, and F are complete on the
delivery view. B1 (markdown control-plane scaffold) and B2
(Definition of Ready, Definition of Done, dependency map, risk
register) landed previously; Slice C subsequently landed on the
canonical branch as PR #12 (`1cfb955 ci: add baseline governance
validation controls`), introducing the file-based `.github/`
baseline (validation workflow, PR template, branch protection
policy file); Slice D has since landed on the canonical branch
as commit `6058661 docs: define reviewer evidence gate for Slice D`,
introducing the three Slice D delivery docs
(`docs/delivery/REVIEW_GATE.md`,
`docs/delivery/REVIEW_EVIDENCE_TEMPLATE.md`,
`docs/delivery/REVIEWER_IDENTITY_REQUIREMENTS.md`) with minimal
coherence updates to the existing delivery docs; Slice E
subsequently landed on the canonical branch as PR #14 / commit
`3cb0266 docs: add Sprint 0 Slice E assignment runtime protocol`,
introducing the five Slice E delivery docs
(`docs/delivery/ASSIGNMENT_ENVELOPE_TEMPLATE.md`,
`docs/delivery/WORKTREE_RUNTIME_PROTOCOL.md`,
`docs/delivery/ENVELOPE_CONSUMPTION_CHECKLIST.md`,
`docs/delivery/SCOPE_AUDIT_CHECKLIST.md`,
`docs/delivery/ASSIGNMENT_ENVELOPE_DRY_RUN.md`) with minimal
coherence updates to the existing delivery docs; and Slice F has
now landed on the canonical branch as PR #16 / commit
`cb7f94a docs: add Slice F release deploy governance policy`,
introducing the five Slice F delivery docs
(`docs/delivery/RELEASE_DEPLOY_GOVERNANCE.md`,
`docs/delivery/RELEASE_CANDIDATE_CHECKLIST.md`,
`docs/delivery/MERGE_APPROVAL_CHECKLIST.md`,
`docs/delivery/DEPLOYMENT_APPROVAL_POLICY.md`,
`docs/delivery/ROLLBACK_AND_POST_RELEASE_EVIDENCE.md`) with minimal
coherence updates to the existing delivery docs. Delivery-view
backlog rows remain markdown-only; structured YAML sidecars
deferred to B3. Live GitHub branch protection settings on the
remote repository remain a separate privileged future decision and
are not mutated by PR #12, PR #14, or PR #16. The canonical-view
Slice F row in §c.6 is now `Done` with durable evidence PR #16 /
`cb7f94a`. Post-Sprint-0 substrate has since landed: PR #20
(`35bf85f docs: add open-source readiness materials (#20)`) and
PR #21 (`5b762f9 fix: remediate public launch readiness blockers
(#21)`) added open-source and public-launch readiness substrate;
PR #22 (`d892cd3 feat: add workflow hardening controls (#22)`) and
PR #23 (`3dc45a1 fix: harden workflow validator follow-ups (#23)`)
added and hardened the workflow-hardening protocol substrate. See
§e.8 and §e.9. CFC-1 (`post-sprint-0/cfc-1-codex-first-class`)
governance scope and operations protocol substrate has landed on the
canonical branch as PR #25 / merge commit `30a3e8c`; see §e.10. CFC
follow-on Batch 2A (`post-sprint-0/cfc-2a-codex-role-decision`)
landed on the canonical branch as PR #27 / merge commit `6b51882
docs: draft Codex role authority decision (#27)`; see §e.11. CFC
follow-on Batch 2B (`post-sprint-0/cfc-2b-codex-architecture-matrix`)
landed on the canonical branch as PR #28 / merge commit `c06a3e7
docs: encode Codex architecture matrix role decision`; see §e.12.
CFC follow-on Batch 2C
(`post-sprint-0/cfc-2c-codex-identity-decision`) has landed on the
canonical branch as PR #29 / merge commit `66a8074 docs: draft Codex
identity record encoding decision (#29)`; see §e.13. Source ratified
eight §6 decisions. The Codex identity record authoring envelope
(`post-sprint-0/cfc-codex-identity-record-authoring`) has since landed
on the canonical branch as PR #31 / merge commit `78b57a4 docs: author
Codex identity record (#31)`; see §e.14. The next gate is Batch 2D
(review/architect/implementer evidence schema, privileged
`schema`-class), which requires a separately Source-ratified
schema-class envelope before any Batch 2D implementation.

**Scope**: Governed Creator Engine work items only. Repo-visible
artifacts here are canonical; external tracker entries (if any) are
non-canonical references only. A fresh clone is sufficient to identify
the next recommended task; no external credentials or network state
are required.

See [`./README.md`](./README.md) for the source-of-truth relationship,
the tracker boundary, and the anti-Jira-clone statement. This document
is part of the **minimum repo-native delivery control plane** and is
**not a Jira clone**.

## a. Status vocabulary (delivery view only)

This backlog uses an eight-column **delivery view** vocabulary. These
statuses are layered on top of, and do not amend, the Feature 001
spec-status lifecycle (`draft → ready → in_progress → verified →
ratified → done`, FR-013a). A delivery item's status describes how it
appears on the Kanban board; the underlying spec/plan/tasks artifacts
retain their canonical lifecycle values.

| Delivery status | Meaning |
|---|---|
| `Backlog` | Identified work that is not yet selected or shaped enough to start. |
| `Ready` | Shaped, dependencies satisfied, and eligible to be pulled into an Assignment Envelope. |
| `In Progress` | Inside an active Assignment Envelope, before independent verification completes. |
| `Verified` | Local validation and independent review evidence recorded; awaiting ratification. |
| `Ratified` | Source ratification recorded; merge authorized but not yet executed (or executed but post-merge evidence incomplete). |
| `Done` | Merged on the canonical branch with finalized attestation. |
| `Deferred` | Intentionally not in scope for the current sprint, with a named owning future slice or feature. |
| `Blocked` | Cannot advance until a named blocker clears; the blocker is the implied next task. |

The delivery view MUST NOT be used to amend, skip, or backfill the
Feature 001 lifecycle. Skipping or backfilling Feature 001 lifecycle
states is a contract violation per FR-027a.

## b. Work-item fields

Every backlog row below carries these fields. Field semantics:

- **id**: stable identifier within this backlog (e.g.,
  `sprint-0/slice-b1`).
- **parent**: parent epic / slice / feature id, or `—` for top-level.
- **status**: a delivery-view status from §a.
- **scope**: one-line scope summary; deferrals are explicit.
- **acceptance gate**: the condition that promotes the item to
  `Done` (typically references the Sprint 0 exit gates in
  [`../../specs/sprint-0-minimum-viable-delivery-system/README.md`](../../specs/sprint-0-minimum-viable-delivery-system/README.md)
  §4 or a feature acceptance criterion).
- **dependencies / blockers**: ids of items that must reach `Done`
  (or `Ratified`) before this item can advance; `—` if none.
- **anticipated mutation class**: Feature 001 baseline class expected
  to dominate the work item (`docs`, `code`, `schema`, `deploy`,
  `governance`, `identity`, `security`, `attestation`, `redaction`),
  per [`../governance/MUTATION_CLASS_MODEL.md`](../governance/MUTATION_CLASS_MODEL.md).
- **owner role**: Feature 001 baseline role category expected to
  author the work (`source`, `ratifier`, `reviewer`, `architect`,
  `implementer`, `verifier`, `observer`), per
  [`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md).
- **ratifier role**: required ratifier role (`source` for privileged
  classes per FR-008; `source` or a `source`-delegated `ratifier` for
  non-privileged classes once delegation is ratified).
- **external tracker reference** *(optional, non-canonical)*: an
  external tracker id (e.g., `ENG-1234`) MAY appear here as a
  reference only. It is not a substitute for any repo-visible artifact
  or for Source ratification. Absence here is the default.

These fields are the backlog's compact row schema. They are
intentionally minimal so the backlog remains a row catalog and not a
Jira clone. Definition of Ready, Definition of Done, dependency-map
elaboration, and risk handling live in the B2 documents
([`./DEFINITION_OF_READY.md`](./DEFINITION_OF_READY.md),
[`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md),
[`./DEPENDENCIES.md`](./DEPENDENCIES.md),
[`./RISK_REGISTER.md`](./RISK_REGISTER.md)); this section names only
the fields a backlog row carries.

## c. Sprint 0 — Minimum Viable Delivery System

Owning source of truth:
[`../../specs/sprint-0-minimum-viable-delivery-system/README.md`](../../specs/sprint-0-minimum-viable-delivery-system/README.md).

### c.1 Slice A — Canonical documentation set

- **id**: `sprint-0/slice-a`
- **parent**: `sprint-0`
- **status**: `Done`
- **scope**: Author the 17 Feature 002 canonical documents under
  `docs/product/`, `docs/architecture/`, `docs/governance/`,
  `docs/quality/`, `docs/devops/`, `docs/security/`.
- **acceptance gate**: Sprint 0 exit gate #1
  (17 canonical documents exist and satisfy Feature 002 acceptance
  criteria).
- **dependencies / blockers**: —
- **anticipated mutation class**: `docs`
- **owner role**: `architect` (drafter); `implementer` (final
  authoring)
- **ratifier role**: `source`
- **external tracker reference**: —
- **durable evidence**: merged commits
  `51a885e docs: integrate Sprint 0 Slice A canonical docs (#5)` and
  `7cc082f docs: harden Slice A post-merge references (#6)` on the
  canonical branch.

### c.2 Slice B — Repo-native delivery control plane

- **id**: `sprint-0/slice-b`
- **parent**: `sprint-0`
- **status**: `Done`
- **scope**: Establish the minimum repo-native delivery control plane
  required to answer "what is next?" after every merge. Comprises B1
  (markdown control-plane scaffold) and B2 (Definition of Ready,
  Definition of Done, dependency map, risk register). B3 and B4
  remain deferred.
- **acceptance gate**: Sprint 0 exit gates #2 (repo-native
  roadmap/backlog/Kanban) and #3 (post-merge next-task protocol).
  Both B1 and B2 must reach `Ratified` or `Done` for Slice B to be
  complete on the delivery view. Both B1 and B2 have now landed on
  the canonical branch (see §c.2.1 and §c.2.2 durable evidence).
- **dependencies / blockers**: `sprint-0/slice-a` (Done).
- **anticipated mutation class**: `docs`
- **owner role**: `architect` / `implementer`
- **ratifier role**: `source`
- **external tracker reference**: —
- **durable evidence**: B1 and B2 merged on the canonical branch (see
  §c.2.1 and §c.2.2). With both sub-batches landed, Slice B is
  complete on the delivery view.

#### c.2.1 Slice B1 — Markdown control-plane scaffold (Source-ratified)

- **id**: `sprint-0/slice-b/b1`
- **parent**: `sprint-0/slice-b`
- **status**: `Done`
- **scope**: Create `docs/delivery/README.md`, `BACKLOG.md`,
  `KANBAN.md`, and `NEXT_TASK_PROTOCOL.md` under the Source-ratified
  envelope-equivalent posture; markdown-only; no `.github/`,
  `specs/`, or structured YAML sidecar mutation. DoR / DoD /
  dependency map / risk register are covered by B2 and were not part
  of the B1 commit boundary.
- **acceptance gate**: B1 docs validate against the envelope's
  content-smoke check; Source ratifies the scaffold; the
  canonical-branch merge finalizes B1 to `Done`.
- **dependencies / blockers**: `sprint-0/slice-a` (Done).
- **anticipated mutation class**: `docs`
- **owner role**: `implementer` (Claude Code under Hermes envelope)
- **ratifier role**: `source`
- **external tracker reference**: —
- **durable evidence**: merged commit
  `77e0bfe docs: add Sprint 0 Slice B1 delivery control plane (#7)`
  on the canonical branch.

#### c.2.2 Slice B2 — DoR / DoD / dependency map / risk register

- **id**: `sprint-0/slice-b/b2`
- **parent**: `sprint-0/slice-b`
- **status**: `Done`
- **scope**: Author `docs/delivery/DEFINITION_OF_READY.md`,
  `DEFINITION_OF_DONE.md`, `DEPENDENCIES.md`, and `RISK_REGISTER.md`,
  layered onto Feature 001 FR-013 / FR-013a / FR-014 and the Sprint 0
  execution sequence. Minimal updates to the B1 README, backlog,
  Kanban, and next-task protocol are included only for
  discoverability and status coherence. Still markdown-only.
- **acceptance gate**: Sprint 0 exit gate #2 fully satisfied;
  post-merge next-task protocol references a complete delivery
  control plane.
- **dependencies / blockers**: `sprint-0/slice-b/b1` (`Done`).
- **anticipated mutation class**: `docs`
- **owner role**: `architect` / `implementer`
- **ratifier role**: `source`
- **external tracker reference**: —
- **durable evidence**: merged commit
  `d4a2636 docs: add Sprint 0 Slice B2 readiness controls (#10)`
  on the canonical branch.

#### c.2.3 Slice B3 — Structured YAML backlog sidecars (deferred)

- **id**: `sprint-0/slice-b/b3`
- **parent**: `sprint-0/slice-b`
- **status**: `Deferred`
- **scope**: Optional structured YAML sidecars for backlog work
  items, only if Source later ratifies a schema. Not required for
  Sprint 0 exit.
- **acceptance gate**: Source ratifies a sidecar schema; the
  validator surfaces sidecar violations.
- **dependencies / blockers**: `sprint-0/slice-b/b2`.
- **anticipated mutation class**: `schema` / `docs`
- **owner role**: `architect` / `verifier`
- **ratifier role**: `source`
- **external tracker reference**: —

#### c.2.4 Slice B4 — Optional external-tracker mirror/adapter (deferred)

- **id**: `sprint-0/slice-b/b4`
- **parent**: `sprint-0/slice-b`
- **status**: `Deferred`
- **scope**: Optional design of a non-canonical mirror or adapter for
  one of Jira / Linear / GitHub Projects: directionality, mapping
  rules, conflict resolution, credential policy, audit evidence.
  Repo-visible backlog remains canonical regardless.
- **acceptance gate**: Source ratifies an adapter design; the
  adapter respects the tracker boundary in
  [`./README.md`](./README.md) §d.
- **dependencies / blockers**: `sprint-0/slice-b/b2`. Implementation
  requires separate Source ratification beyond the design.
- **anticipated mutation class**: `governance` (design) / `code`
  (later implementation)
- **owner role**: `architect`
- **ratifier role**: `source`
- **external tracker reference**: —

### c.3 Slice C — Thin GitHub / CI / PR governance

- **id**: `sprint-0/slice-c`
- **parent**: `sprint-0`
- **status**: `Done`
- **scope**: `.github/workflows/` baseline validation workflow; PR
  template; branch protection policy file; review policy /
  CODEOWNERS policy as applicable; CI evidence rule
  (verifies-not-ratifies). PR #12 landed the validation workflow,
  PR template, and branch protection policy file; CODEOWNERS was
  not included under the "as applicable" qualifier. Live GitHub
  branch protection settings on the remote repository remain a
  separate privileged future decision and were not mutated.
- **acceptance gate**: Sprint 0 exit gates #4 (PR validation), #5
  (PR template and review policy), #6 (branch protection policy).
- **dependencies / blockers**: `sprint-0/slice-b` is `Done` (the
  delivery-view predecessor edge was cleared before consumption);
  Slice C has since been Source-ratified as a privileged
  `governance` envelope and merged on the canonical branch.
- **anticipated mutation class**: `governance` (privileged); some
  `docs` for policy text.
- **owner role**: `architect` (policy) / `implementer` (workflows)
- **ratifier role**: `source`
- **external tracker reference**: —
- **durable evidence**: merged commit
  `1cfb955 ci: add baseline governance validation controls (#12)`
  on the canonical branch, landing `.github/workflows/validate.yml`,
  `.github/pull_request_template.md`, and
  `.github/BRANCH_PROTECTION_POLICY.md`.

### c.4 Slice D — Minimum review / QA / identity governance

- **id**: `sprint-0/slice-d`
- **parent**: `sprint-0`
- **status**: `Done`
- **scope**: Generic reviewer identity record **pattern** (not an
  instantiated identity); generic markdown-equivalent QA / review
  evidence template; review-gate definition; standing invariant that
  review evidence is **not Source ratification**. Implementation
  remains project-, tenant-, runtime-, model-, and harness-agnostic;
  concrete tool / model / host / actor / account bindings are
  deployment-time overlay decisions and are not selected upstream by
  this slice.
- **acceptance gate**: Sprint 0 exit gates #7 (governed roles) and
  #10 (QA / review evidence format).
- **dependencies / blockers**: `sprint-0/slice-c` is `Done`; the
  Slice D privileged `identity` / `docs` envelope was Source-
  ratified and the batch has now landed on the canonical branch.
  Author/approver separation was preserved: the visible
  implementation agent authored the Slice D artifacts and did not
  ratify them.
- **anticipated mutation class**: `identity` (privileged) / `docs`
- **owner role**: `architect` (policy) / `implementer` (markdown
  authoring under the Source-ratified visible implementation
  envelope)
- **ratifier role**: `source`
- **external tracker reference**: —
- **durable evidence**: merged commit
  `6058661 docs: define reviewer evidence gate for Slice D` on the
  canonical branch, landing
  `docs/delivery/REVIEWER_IDENTITY_REQUIREMENTS.md`,
  `docs/delivery/REVIEW_EVIDENCE_TEMPLATE.md`, and
  `docs/delivery/REVIEW_GATE.md`, with minimal coherence updates to
  `docs/delivery/README.md`, `docs/delivery/BACKLOG.md`,
  `docs/delivery/KANBAN.md`, and `docs/delivery/DEPENDENCIES.md`.

### c.5 Slice E — Manual Assignment Envelope and worktree runtime protocol

- **id**: `sprint-0/slice-e`
- **parent**: `sprint-0`
- **status**: `Done`
- **scope**: Assignment Envelope template; worktree/branch naming
  conventions; one-driver-per-worktree rule documentation; envelope
  consumption and scope-audit checklists; dry-run evidence for at
  least one envelope.
- **acceptance gate**: Sprint 0 exit gates #8 (Assignment Envelope
  template + dry-run) and #9 (worktree/branch naming +
  one-driver-per-worktree).
- **dependencies / blockers**: `sprint-0/slice-c` is `Done` and
  `sprint-0/slice-d` is `Done`; the delivery-view predecessor edges
  cleared and the Slice E authoring envelope was subsequently
  Source-ratified as a bounded docs-only `governance` / `docs`
  batch. The Slice E authoring batch has now landed on the
  canonical branch.
- **anticipated mutation class**: `governance` (privileged) / `docs`
- **owner role**: `architect`
- **ratifier role**: `source`
- **external tracker reference**: —
- **durable evidence**: merged commit
  `3cb0266 docs: add Sprint 0 Slice E assignment runtime protocol (#14)`
  on the canonical branch, landing
  [`./ASSIGNMENT_ENVELOPE_TEMPLATE.md`](./ASSIGNMENT_ENVELOPE_TEMPLATE.md),
  [`./WORKTREE_RUNTIME_PROTOCOL.md`](./WORKTREE_RUNTIME_PROTOCOL.md),
  [`./ENVELOPE_CONSUMPTION_CHECKLIST.md`](./ENVELOPE_CONSUMPTION_CHECKLIST.md),
  [`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md), and
  [`./ASSIGNMENT_ENVELOPE_DRY_RUN.md`](./ASSIGNMENT_ENVELOPE_DRY_RUN.md),
  with minimal coherence updates to existing delivery docs.

### c.6 Slice F — Release / deploy governance policy

- **id**: `sprint-0/slice-f`
- **parent**: `sprint-0`
- **status**: `Done`
- **scope**: Release-candidate checklist; merge-approval checklist;
  deployment-approval policy; rollback/evidence expectations; explicit
  deploy mutation ratification rule; statement of currently absent
  deployment targets/environments.
- **acceptance gate**: Sprint 0 exit gate #11 (release / merge /
  deploy governance documented) and confirmation that gate #12
  (Feature 003+ sequenced) is satisfied.
- **dependencies / blockers**: `sprint-0/slice-e` is `Done`; the
  delivery-view predecessor edge from Slice E was cleared (durable
  evidence PR #14 / `3cb0266`). The Slice F authoring envelope was
  Source-ratified as a bounded docs-only `governance` / `docs`
  policy-authoring batch and has now landed on the canonical
  branch. No deploy automation is implemented under Sprint 0; this
  slice authored policy only. Live deploy automation, GitHub
  environments, branch protection settings, CODEOWNERS, and
  Feature 006 deploy execution remain separate privileged future
  decisions and are not authorized by Slice F landing.
- **anticipated mutation class**: `deploy` (privileged) / `docs`
- **owner role**: `architect`
- **ratifier role**: `source`
- **external tracker reference**: —
- **durable evidence**: merged commit
  `cb7f94a docs: add Slice F release deploy governance policy (#16)`
  on the canonical branch, landing
  [`./RELEASE_DEPLOY_GOVERNANCE.md`](./RELEASE_DEPLOY_GOVERNANCE.md),
  [`./RELEASE_CANDIDATE_CHECKLIST.md`](./RELEASE_CANDIDATE_CHECKLIST.md),
  [`./MERGE_APPROVAL_CHECKLIST.md`](./MERGE_APPROVAL_CHECKLIST.md),
  [`./DEPLOYMENT_APPROVAL_POLICY.md`](./DEPLOYMENT_APPROVAL_POLICY.md),
  and
  [`./ROLLBACK_AND_POST_RELEASE_EVIDENCE.md`](./ROLLBACK_AND_POST_RELEASE_EVIDENCE.md),
  with minimal coherence updates to existing delivery docs.

## d. Specific reserved item — US3 A1

- **id**: `us3/a1`
- **parent**: (later feature scope; not yet specced under Sprint 0
  exit gates)
- **status**: `Blocked` / `Deferred`
- **scope**: Reserved reference to the previously discussed "US3 A1"
  area. **Implementation is not authorized** under this batch or under
  Sprint 0. The item is recorded here only so that any future Source
  ratification has a referenceable id, and so that a fresh clone can
  see it is blocked.
- **acceptance gate**: Source explicitly ratifies a future spec
  authorizing US3 A1; until then this item does not advance past
  `Blocked` / `Deferred`.
- **dependencies / blockers**: Sprint 0 must reach exit before any
  later-feature US3 work can be authorized; an explicit Source
  ratification is also required.
- **anticipated mutation class**: to be determined by the future spec;
  treat as potentially privileged until classified.
- **owner role**: `architect` (when later specced)
- **ratifier role**: `source`
- **external tracker reference**: —

## e. Post-Sprint-0 feature backlog (scope summary)

These rows summarize the Feature 001–006 and v1.0 scope from
[`../product/ROADMAP.md`](../product/ROADMAP.md) without duplicating
the roadmap body. They are intentionally terse; the roadmap remains
the source of truth. Post-Sprint-0 substrate items that have landed
on the canonical branch but are not Feature 001–006 scope are
recorded as §e.8 and §e.9.

### e.1 Feature 001 — v0.1 governance substrate

- **id**: `feature-001`
- **parent**: —
- **status**: `Done`
- **scope**: Substrate contracts (identity, attestation, mutation
  classes, authority matrix, Definition of Ready / Done, ratification
  flow, redaction gate, validator, dogfood tenant fixture, examples,
  verification spec). See `specs/001-v0-1-governance-substrate/`.
- **acceptance gate**: Feature 001 spec acceptance criteria; merged.
- **dependencies / blockers**: —
- **anticipated mutation class**: `governance` / `schema` /
  `docs` / `code` (validator)
- **owner role**: `architect` / `implementer` / `verifier`
- **ratifier role**: `source`
- **external tracker reference**: —

### e.2 Feature 002 — v0.1-docs operating model

- **id**: `feature-002`
- **parent**: —
- **status**: `Done`
- **scope**: Operating-model specification only at the substrate
  layer; canonical document bodies authored under Slice A.
- **acceptance gate**: Feature 002 spec acceptance criteria; merged.
  Slice A satisfies the canonical-documents subset.
- **dependencies / blockers**: —
- **anticipated mutation class**: `docs`
- **owner role**: `architect`
- **ratifier role**: `source`
- **external tracker reference**: —
- **durable evidence**: merged commit
  `4ab7962 feat: add Creator Engine governance substrate and SDLC operating model (#2)`
  on the canonical branch (Feature 002 spec); canonical document
  bodies merged under `sprint-0/slice-a` (see §c.1).

### e.3 Feature 003 — GitHub CI governance

- **id**: `feature-003`
- **parent**: —
- **status**: `Deferred`
- **scope**: `.github/workflows/` baseline validation, PR template,
  branch protection policy (and live GitHub settings if Source
  ratifies that mutation), review policy / CODEOWNERS as applicable,
  CI evidence rule.
- **acceptance gate**: Feature 003 spec ratified and implementation
  acceptance criteria met; Sprint 0 Slice C provides the policy
  outline that Feature 003 instantiates.
- **dependencies / blockers**: `sprint-0/slice-c` is `Done` (PR #12
  landed the file-based `.github/` baseline), so the predecessor
  edge is cleared. Feature 003 nonetheless remains `Deferred`
  pending its own Source-ratified privileged envelope for any live
  GitHub branch protection settings on the remote repository,
  CODEOWNERS, or further extension of the landed `.github/`
  baseline; Slice C landing does not by itself authorize Feature
  003 implementation.
- **anticipated mutation class**: `governance` (privileged)
- **owner role**: `architect` / `implementer`
- **ratifier role**: `source`
- **external tracker reference**: —

### e.4 Feature 004 — Independent review / QA agent evidence

- **id**: `feature-004`
- **parent**: —
- **status**: `Deferred`
- **scope**: Codex reviewer identity record, QA agent identity
  record, security agent identity record, review/QA/security evidence
  schemas, review gate definition.
- **acceptance gate**: Feature 004 spec ratified; identities
  instantiated per Feature 001 contract; evidence schemas validate.
- **dependencies / blockers**: `sprint-0/slice-d`; `feature-001`
  (substrate) and `feature-002` (operating model) already merged.
- **anticipated mutation class**: `identity` (privileged)
- **owner role**: `architect`
- **ratifier role**: `source`
- **external tracker reference**: —

### e.5 Feature 005 — Dispatch / worktree / sandbox runtime

- **id**: `feature-005`
- **parent**: —
- **status**: `Deferred`
- **scope**: Hermes dispatcher automation; worktree lifecycle
  automation; sandboxing; safe parallel runtime; conflict detection
  mapping to the four-class taxonomy.
- **acceptance gate**: Feature 005 spec ratified; manual envelope
  protocol from `sprint-0/slice-e` already rehearsed.
- **dependencies / blockers**: `sprint-0/slice-e`.
- **anticipated mutation class**: `governance` (privileged) /
  `code`
- **owner role**: `architect` / `implementer`
- **ratifier role**: `source`
- **external tracker reference**: —

### e.6 Feature 006 — Release / deployment governance

- **id**: `feature-006`
- **parent**: —
- **status**: `Deferred`
- **scope**: Release agent identity record; release records, deploy
  attestations, rollback evidence; GitHub environments and gates;
  Source-approved deploy gates for SDLC transitions T22–T24;
  release-readiness checklist.
- **acceptance gate**: Feature 006 spec ratified; deploy targets
  declared by Source before automation implementation. The `deploy`
  class remains Source-only per Feature 001 FR-008 regardless of
  automation.
- **dependencies / blockers**: `sprint-0/slice-f`; deploy targets
  do not yet exist.
- **anticipated mutation class**: `deploy` (privileged)
- **owner role**: `architect` / `implementer`
- **ratifier role**: `source`
- **external tracker reference**: —

### e.7 v1.0 — End-to-end governed agentic SDLC loop (integration target)

- **id**: `v1.0`
- **parent**: —
- **status**: `Deferred`
- **scope**: Integration target reached when Features 001–006 have
  landed and the full SDLC state machine is exercised end-to-end with
  every privileged gate human-ratified. Not a feature; an integration
  target.
- **acceptance gate**: Sprint 0 exit gates 1–12 satisfied;
  Features 003–006 ratified and implemented; substrate validator
  passing on the reference tenant.
- **dependencies / blockers**: `feature-003`, `feature-004`,
  `feature-005`, `feature-006`, and full Sprint 0 exit.
- **anticipated mutation class**: integration; multiple privileged
  classes touched across the feature set.
- **owner role**: `source` (integration ratifier) / `architect`
- **ratifier role**: `source`
- **external tracker reference**: —

### e.8 Post-Sprint-0 substrate — open-source / public-launch readiness

- **id**: `post-sprint-0/oss-readiness`
- **parent**: —
- **status**: `Done`
- **scope**: Open-source readiness materials (PR #20) and
  public-launch readiness blocker remediation (PR #21).
  Post-Sprint-0 substrate; not a Sprint 0 Slice A-F item.
- **acceptance gate**: Merged on the canonical branch with durable
  commit evidence.
- **dependencies / blockers**: —
- **anticipated mutation class**: `docs`
- **owner role**: `implementer`
- **ratifier role**: `source`
- **external tracker reference**: —
- **durable evidence**: merged commits `35bf85f docs: add
  open-source readiness materials (#20)` and `5b762f9 fix:
  remediate public launch readiness blockers (#21)` on the
  canonical branch.

### e.9 Post-Sprint-0 substrate — workflow-hardening protocol

- **id**: `post-sprint-0/workflow-hardening`
- **parent**: —
- **status**: `Done`
- **scope**: Workflow-hardening controls: operations protocol docs
  (`docs/operations/CONTROLLER_BOUNDARY_POLICY.md`,
  `NO_COPY_PASTE_PATTERN.md`, `PATH_MANIFEST_FIDELITY_PROTOCOL.md`,
  `TRANSCRIPT_ARCHIVE_PROTOCOL.md`), schemas, templates, validator
  checks, and CI validator hardening. Provides durable landed
  evidence for R-011 and R-012 mitigations in
  [`./RISK_REGISTER.md`](./RISK_REGISTER.md). Post-Sprint-0
  substrate; not a Sprint 0 Slice A-F item.
- **acceptance gate**: Merged on the canonical branch with durable
  commit evidence.
- **dependencies / blockers**: —
- **anticipated mutation class**: `docs` / `code` (validator)
- **owner role**: `implementer`
- **ratifier role**: `source`
- **external tracker reference**: —
- **durable evidence**: merged commits `d892cd3 feat: add workflow
  hardening controls (#22)` and `3dc45a1 fix: harden workflow
  validator follow-ups (#23)` on the canonical branch.

### e.10 Post-Sprint-0 substrate — CFC-1: Codex first-class actor envelope (Batch 1)

- **id**: `post-sprint-0/cfc-1-codex-first-class`
- **parent**: —
- **status**: `Done`
- **scope**: Governance scope document
  (`docs/governance/CODEX_FIRST_CLASS_SCOPE.md`) and operations
  protocol (`docs/operations/CODEX_FIRST_CLASS_PROTOCOL.md`)
  establishing the bounded scope/protocol substrate for making Codex
  first-class later, without instantiating Codex identity, creating
  review-evidence schemas, updating the architecture actor/tool
  matrix, expanding Codex authority, binding any
  provider/tool/model/host/account, mutating GitHub settings, or
  implementing Feature 005 dispatch automation. Batch 1 mutation
  class: `governance` / `docs`. Delivery docs updated for
  discoverability (`docs/delivery/BACKLOG.md`, `KANBAN.md`,
  `DEPENDENCIES.md`, `README.md`, `RISK_REGISTER.md`). Privileged
  Codex identity record, review-evidence schema, architecture
  actor/tool matrix update, and Codex authority expansion are
  explicitly deferred to a later Source-ratified Feature 004/CFC
  follow-on envelope.
- **acceptance gate**: Batch 1 governance scope and operations
  protocol documents validate; delivery docs are coherent; Source
  ratification is recorded; merged on the canonical branch with
  finalized attestation.
- **dependencies / blockers**: Sprint 0 Slices A–F (`Done`);
  `post-sprint-0/oss-readiness` (`Done`);
  `post-sprint-0/workflow-hardening` (`Done`). Each of these
  predecessor edges is cleared. Feature 004/CFC follow-on identity
  and schema work depends on this item reaching `Done` and requires
  its own Source-ratified privileged envelope; it does not unblock
  here.
- **anticipated mutation class**: `governance` / `docs`
- **owner role**: `implementer` (Claude Code under Hermes envelope);
  `controller` / `reviewer` (Nefarious)
- **ratifier role**: `source`
- **external tracker reference**: —
- **durable evidence**: merged commit
  `30a3e8c docs: add CFC-1 scope and protocol envelope (#25)` on the
  canonical branch.

### e.11 Post-Sprint-0 substrate — CFC follow-on Batch 2A: Codex role/authority decision request

- **id**: `post-sprint-0/cfc-2a-codex-role-decision`
- **parent**: —
- **status**: `Done`
- **scope**: Decision-request artifact at
  `docs/governance/CODEX_ROLE_AND_AUTHORITY_DECISION.md` letting
  Source explicitly decide Codex role and authority semantics
  before any architecture actor/tool matrix update, Codex identity
  record, review/architect-evidence schema, validator, template,
  example, provider/tool/model/host/account binding, or authority
  expansion. Enumerates candidate `role_category` mappings
  (`architect`, `implementer`, both, `reviewer`, new role) with
  invariants, downstream consequences for Batch 2B / 2C / 2D, and
  FR-015 / baseline authority-matrix coverage consequences;
  reaffirms that the seven-row baseline authority-matrix rule is
  not amended by Batch 2A and that
  `docs/contracts/authority-matrix.yml` is not mutated. Lists
  seven discrete Source decisions: Codex `role_category`; Codex
  allowed mutation classes for Phase 1; Codex authority boundary
  (architect parity is authoring parity, not ratification / merge
  / deploy authority); provider/tool/model/host/account binding
  posture; review-evidence semantics under architect framing;
  public/tenant role label; reaffirmation of authority-matrix
  non-mutation. Minimal coherence updates to
  `docs/governance/CODEX_FIRST_CLASS_SCOPE.md` §5,
  `docs/delivery/BACKLOG.md` §e, `docs/delivery/KANBAN.md`, and
  `docs/delivery/DEPENDENCIES.md` are part of the five-path
  manifest. Privileged Codex identity record, evidence schema,
  architecture actor/tool matrix update, provider binding, and
  authority expansion are explicitly **not** authorized by Batch
  2A; they are deferred to separately Source-ratified Batch 2B /
  2C / 2D / later envelopes.
- **acceptance gate**: Batch 2A decision document and coherence
  updates validate against the substrate validator and the
  five-path manifest fidelity check; Source ratifies one option
  from the seven §6 decisions in
  `docs/governance/CODEX_ROLE_AND_AUTHORITY_DECISION.md`; merged
  on the canonical branch with finalized attestation.
- **dependencies / blockers**:
  `post-sprint-0/cfc-1-codex-first-class` (`Done`, PR #25 /
  `30a3e8c`). Successor Batches 2B (architecture actor/tool
  matrix update), 2C (Codex identity record encoding decision
  request), and 2D (review/architect/implementer-evidence schema)
  each require their own Source-ratified envelopes; 2B has since
  landed (see §e.12), 2C has since landed (see §e.13), and Codex
  identity record authoring has since landed (see §e.14); the current
  downstream gate is the Batch 2D review/architect/implementer evidence
  schema, a separately Source-ratified privileged `schema`-class
  envelope required before implementation.
- **anticipated mutation class**: `governance` / `docs`
- **owner role**: `architect` (drafter) / `implementer` (markdown
  authoring under the Source-ratified visible implementation
  envelope); `controller` / `reviewer` (Nefarious)
- **ratifier role**: `source`
- **external tracker reference**: —
- **durable evidence**: merged commit
  `6b51882 docs: draft Codex role authority decision (#27)` on the
  canonical branch. Source ratified Option C (per-batch
  architect/implementer authoring assignment); Phase-1 allowed
  mutation classes = `governance`, `docs`, and `code` (with `code`
  gated to implementer-class envelopes; privileged classes remain
  Source-ratified); provider/tool/model/host/account binding remains
  placeholder/unbound; review evidence retained as a separate
  artifact class; `codex-architect` is a tenant/public overlay alias
  only, not a new baseline `role_category` row;
  `docs/contracts/authority-matrix.yml` was not mutated.

### e.12 Post-Sprint-0 substrate — CFC follow-on Batch 2B: Codex architecture actor/tool matrix update

- **id**: `post-sprint-0/cfc-2b-codex-architecture-matrix`
- **parent**: —
- **status**: `Done`
- **scope**: Architecture actor/tool matrix update instantiating the
  Batch 2A §6.1 Option C role choice in
  `docs/architecture/agent-interaction-model.md` §a (Codex row) and
  §b.4 (per-batch governed authoring / review pattern). Authority is
  worded as **envelope-bound, not personality-bound**: an
  architect-class envelope authorizes architect authoring; an
  implementer-class envelope authorizes implementer authoring. Codex
  retains authoring parity only — no ratification, merge, or deploy
  authority. `codex-architect` is named as a tenant/public overlay
  alias, not a new baseline `role_category` row. The Batch 2B
  envelope is `governance` / `docs`-class and does not mutate
  `docs/contracts/identity-record.md`,
  `docs/contracts/authority-matrix.md`,
  `schemas/`, validators, templates, examples, tenants, or
  `.github/`. Codex identity record creation, review/architect/
  implementer-evidence schemas, and provider binding remain deferred.
- **acceptance gate**: Batch 2B architecture matrix update validates
  against the substrate validator; delivery docs are coherent; Source
  ratification recorded; merged on the canonical branch with finalized
  attestation.
- **dependencies / blockers**:
  `post-sprint-0/cfc-2a-codex-role-decision` (`Done`, PR #27 /
  `6b51882`).
- **anticipated mutation class**: `governance` / `docs`
- **owner role**: `architect` (drafter) / `implementer` (markdown
  authoring under the Source-ratified visible implementation
  envelope); `controller` / `reviewer` (Nefarious)
- **ratifier role**: `source`
- **external tracker reference**: —
- **durable evidence**: merged commit
  `c06a3e7 docs: encode Codex architecture matrix role decision`
  on the canonical branch (PR #28).

### e.13 Post-Sprint-0 substrate — CFC follow-on Batch 2C: Codex identity record encoding decision request

- **id**: `post-sprint-0/cfc-2c-codex-identity-decision`
- **parent**: —
- **status**: `Done`
- **scope**: Decision-request artifact at
  `docs/governance/CODEX_IDENTITY_RECORD_ENCODING_DECISION.md`
  letting Source explicitly decide how the Batch 2A ratified
  Option C semantics (per-batch architect/implementer authoring
  assignment) and the Batch 2B envelope-bound authority wording are
  encoded inside the existing `docs/contracts/identity-record.md`
  substrate, **before** any Codex identity record authoring envelope
  is consumed. Enumerates four candidate encodings under
  single-valued `role_category`: Option A — single record with
  baseline `role_category = architect` (implementer authoring
  authorized solely by implementer-class envelopes); Option B —
  single record with baseline `role_category = implementer`
  (architect authoring authorized solely by architect-class
  envelopes); Option C — two separate Codex identity records
  (one architect, one implementer); Option D — amend the
  identity-record schema to permit multi-valued `role_category`,
  explicitly marked as a heavier `schema`-class privileged
  amendment outside this draft's authority. Lists eight discrete
  Source decisions: identity record encoding; `authority_context`
  fields (including governing spec refs to the Batch 2A role-authority
  decision and the Batch 2B agent-interaction-model wording);
  `human_ratifier_roles` (Source); `allowed_repositories`
  (placeholder/unbound versus concrete); `signing_policy`
  (placeholder/unbound, including whether `commit_signing_method =
  none` remains appropriate); storage paths
  (`attestation_storage_path`, `ratification_storage_path`,
  `redaction_storage_path`); `tenant_id` (placeholder substrate-
  internal slug versus tenant-overlay deferral); and reaffirmation
  that the Batch 2D evidence schema remains downstream and is not
  mutated by Batch 2C. Minimal coherence updates to
  `docs/governance/CODEX_FIRST_CLASS_SCOPE.md`,
  `docs/delivery/BACKLOG.md`, `docs/delivery/KANBAN.md`, and
  `docs/delivery/DEPENDENCIES.md` are part of the historical
  five-path manifest for the original PR #29 commit; the follow-on
  reconciliation gate extends this to the seven-path boundary
  documented in
  `docs/governance/CODEX_IDENTITY_RECORD_ENCODING_DECISION.md` §10.
  Codex identity record creation,
  `docs/contracts/identity-record.md` mutation,
  `schemas/identity-record.schema.yaml` mutation, authority-matrix
  mutation, validator/template/example/tenant mutation,
  `docs/architecture/**` mutation, `.github/**` mutation, provider
  binding, Codex authority expansion, dispatch automation, and
  deploy are explicitly **not** authorized by Batch 2C.
- **acceptance gate**: Batch 2C decision document and coherence
  updates validate against the substrate validator and the historical
  five-path manifest fidelity check (original PR #29 boundary); the
  follow-on reconciliation gate validates against the seven-path
  boundary in
  `docs/governance/CODEX_IDENTITY_RECORD_ENCODING_DECISION.md` §10;
  Source ratified the eight §6 decisions in
  `docs/governance/CODEX_IDENTITY_RECORD_ENCODING_DECISION.md`
  (Option A selected as primary encoding; Option C conservative
  fallback retained; `human_ratifier_roles = ["source"]`;
  placeholder/unbound posture for `allowed_repositories`,
  `signing_policy`, storage paths, and `tenant_id`; Batch 2D
  reaffirmed as downstream); merged on the canonical branch. Gate
  met.
- **dependencies / blockers**:
  `post-sprint-0/cfc-2a-codex-role-decision` (`Done`, PR #27 /
  `6b51882`) and
  `post-sprint-0/cfc-2b-codex-architecture-matrix` (`Done`,
  PR #28 / `c06a3e7`). Successor — a separately Source-ratified
  privileged `identity`-class envelope authoring the Codex identity
  record — depends on Batch 2C reaching `Done`. Batch 2D
  (review/architect/implementer evidence schema, privileged
  `schema`-class) remains downstream of Batch 2C and requires its
  own Source-ratified envelope.
- **anticipated mutation class**: `governance` / `docs`
- **owner role**: `architect` (drafter) / `implementer` (markdown
  authoring under the Source-ratified visible implementation
  envelope); `controller` / `reviewer` (Nefarious)
- **ratifier role**: `source`
- **external tracker reference**: —
- **durable evidence**: merged commit
  `66a8074 docs: draft Codex identity record encoding decision (#29)`
  on the canonical branch. Source ratified Option A (single Codex
  identity record, baseline `role_category = architect`; Option C
  conservative fallback retained); `human_ratifier_roles = ["source"]`;
  placeholder/unbound posture for `allowed_repositories`,
  `signing_policy`, storage paths, and `tenant_id`;
  `docs/contracts/authority-matrix.yml`, schemas, validators,
  templates, examples, tenants, `docs/architecture/**`, and
  `.github/**` not mutated.

### e.14 Post-Sprint-0 substrate — CFC follow-on: Codex identity record authoring

- **id**: `post-sprint-0/cfc-codex-identity-record-authoring`
- **parent**: —
- **status**: `Done`
- **scope**: CFC follow-on Codex identity record authoring under
  the Source-ratified privileged `identity`-class envelope. Authors
  one Codex identity record file with `role_category = architect`
  and `human_ratifier_roles = ["source"]`, plus `attestations/`,
  `ratifications/`, and `redactions/` storage directories under
  `tenants/creator-engine-substrate/codex/`. Encoding posture pins
  from Batch 2C §6.1–§6.7: placeholder/unbound `allowed_repositories`,
  `signing_policy`, and `tenant_id`; no concrete
  provider/tool/model/host/account/repository bound; no schema,
  validator, template, example, contract, or architecture file
  modified. Codex authority not expanded; Batch 2D evidence schema
  remains a separate downstream gate requiring its own
  Source-ratified schema-class envelope.
- **acceptance gate**: Identity record file and storage directories
  exist under `tenants/creator-engine-substrate/codex/` and validate
  against the substrate; Source ratification recorded; merged on the
  canonical branch with finalized attestation. Gate met.
- **dependencies / blockers**:
  `post-sprint-0/cfc-2c-codex-identity-decision` (`Done`, PR #29 /
  `66a8074`). Successor — Batch 2D review/architect/implementer
  evidence schema (privileged `schema`-class) — remains downstream
  and requires its own separately Source-ratified schema-class
  envelope per Feature 001 FR-008.
- **anticipated mutation class**: `identity` (privileged)
- **owner role**: `implementer` (Codex under the Source-ratified
  envelope); `controller` / `reviewer` (Nefarious)
- **ratifier role**: `source`
- **external tracker reference**: —
- **durable evidence**: merged commit
  `78b57a4 docs: author Codex identity record (#31)` on the
  canonical branch. Single Codex identity record with
  `role_category = architect`, `human_ratifier_roles = ["source"]`,
  placeholder/unbound posture for `allowed_repositories`,
  `signing_policy`, and `tenant_id`; storage paths under
  `tenants/creator-engine-substrate/codex/`.

## f. Maintenance rules

1. New backlog entries MUST cite their owning source of truth (Sprint
   0 execution README, ROADMAP, or a ratified spec). Entries that
   cannot cite an upstream source MUST be flagged for Source
   ratification before they advance past `Backlog`.
2. Status transitions on this list MUST follow the rules in
   [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §c. They MUST
   NOT amend the Feature 001 spec-status lifecycle.
3. External tracker references, when present, MUST be marked
   non-canonical and MUST NOT be used to justify status changes by
   themselves.
4. Instance-local facts (absolute filesystem paths, local terminal
   identifiers, in-flight PR numbers, local session queues, secrets,
   credentials, tokens) MUST NOT appear in this file. Merged PR
   numbers in canonical-branch commit subjects MAY be cited as
   historical evidence.
5. This file's maintenance rules are subordinate to
   [`./DEFINITION_OF_READY.md`](./DEFINITION_OF_READY.md) and
   [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) once B2
   reaches `Ratified` or `Done`. Dependency edges between rows are
   navigationally mirrored in
   [`./DEPENDENCIES.md`](./DEPENDENCIES.md); standing risks bearing
   on backlog hygiene live in
   [`./RISK_REGISTER.md`](./RISK_REGISTER.md).
