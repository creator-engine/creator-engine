# Creator Engine Backlog

**Status**: Sprint 0 Slices B, C, and D are complete on the
delivery view. B1 (markdown control-plane scaffold) and B2
(Definition of Ready, Definition of Done, dependency map, risk
register) landed previously; Slice C subsequently landed on the
canonical branch as PR #12 (`1cfb955 ci: add baseline governance
validation controls`), introducing the file-based `.github/`
baseline (validation workflow, PR template, branch protection
policy file); and Slice D has since landed on the canonical branch
as commit `6058661 docs: define reviewer evidence gate for Slice D`,
introducing the three Slice D delivery docs
(`docs/delivery/REVIEW_GATE.md`,
`docs/delivery/REVIEW_EVIDENCE_TEMPLATE.md`,
`docs/delivery/REVIEWER_IDENTITY_REQUIREMENTS.md`) with minimal
coherence updates to the existing delivery docs. Delivery-view
backlog rows remain markdown-only; structured YAML sidecars
deferred to B3. Live GitHub branch protection settings on the
remote repository remain a separate privileged future decision and
are not mutated by PR #12. The Slice E authoring envelope has since been Source-ratified as
a bounded docs-only `governance` / `docs` batch; the Slice E
authoring batch is in flight on the local worktree branch
`docs/sprint0-slice-e-assignment-runtime-protocol` and has not yet
merged. The canonical-view Slice E row in §c.5 remains `Blocked`
until the batch lands.

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
- **status**: `Blocked`
- **scope**: Assignment Envelope template; worktree/branch naming
  conventions; one-driver-per-worktree rule documentation; envelope
  consumption and scope-audit checklists; dry-run evidence for at
  least one envelope. This slice will later define the reusable
  envelope template/runtime protocol; the B1 envelope-equivalent used
  for this batch is a temporary Source-ratified placeholder.
- **acceptance gate**: Sprint 0 exit gates #8 (Assignment Envelope
  template + dry-run) and #9 (worktree/branch naming +
  one-driver-per-worktree).
- **dependencies / blockers**: `sprint-0/slice-c` is `Done` and
  `sprint-0/slice-d` is `Done`; the delivery-view predecessor edges
  have cleared. The Slice E authoring envelope has since been
  Source-ratified as a bounded docs-only `governance` / `docs`
  batch; the Slice E authoring batch is in flight on the local
  worktree branch `docs/sprint0-slice-e-assignment-runtime-protocol`
  (see [`./ASSIGNMENT_ENVELOPE_DRY_RUN.md`](./ASSIGNMENT_ENVELOPE_DRY_RUN.md))
  and has not yet merged. The canonical-view row remains `Blocked`
  until the batch lands; the consumer's authorship halts at the
  named stop line per
  [`./WORKTREE_RUNTIME_PROTOCOL.md`](./WORKTREE_RUNTIME_PROTOCOL.md)
  §j.
- **anticipated mutation class**: `governance` (privileged) / `docs`
- **owner role**: `architect`
- **ratifier role**: `source`
- **external tracker reference**: —

### c.6 Slice F — Release / deploy governance policy

- **id**: `sprint-0/slice-f`
- **parent**: `sprint-0`
- **status**: `Blocked`
- **scope**: Release-candidate checklist; merge-approval checklist;
  deployment-approval policy; rollback/evidence expectations; explicit
  deploy mutation ratification rule; statement of currently absent
  deployment targets/environments.
- **acceptance gate**: Sprint 0 exit gate #11 (release / merge /
  deploy governance documented) and confirmation that gate #12
  (Feature 003+ sequenced) is satisfied.
- **dependencies / blockers**: `sprint-0/slice-e`. No deploy
  automation is implemented under Sprint 0; this slice authors policy
  only.
- **anticipated mutation class**: `deploy` (privileged) / `docs`
- **owner role**: `architect`
- **ratifier role**: `source`
- **external tracker reference**: —

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
the source of truth.

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
