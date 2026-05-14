# Creator Engine Delivery Control Plane

**Status**: Sprint 0 Slices B, C, D, and E are complete on the
delivery view. B1 (markdown control-plane scaffold) and B2
(Definition of Ready, Definition of Done, dependency map, risk
register) landed previously under the Source-ratified posture
(Option C of the Slice B strategy decision); Slice C subsequently
landed on the canonical branch as PR #12 (`1cfb955 ci: add baseline
governance validation controls`), introducing the file-based
`.github/` baseline (validation workflow, PR template, branch
protection policy file); Slice D has since landed on the
canonical branch as commit `6058661 docs: define reviewer evidence
gate for Slice D`, introducing the three Slice D delivery docs
([`./REVIEW_GATE.md`](./REVIEW_GATE.md),
[`./REVIEW_EVIDENCE_TEMPLATE.md`](./REVIEW_EVIDENCE_TEMPLATE.md),
[`./REVIEWER_IDENTITY_REQUIREMENTS.md`](./REVIEWER_IDENTITY_REQUIREMENTS.md))
with minimal coherence updates to the existing delivery docs; and
Slice E has now landed on the canonical branch as PR #14 / commit
`3cb0266 docs: add Sprint 0 Slice E assignment runtime protocol`,
introducing the five Slice E delivery docs
([`./ASSIGNMENT_ENVELOPE_TEMPLATE.md`](./ASSIGNMENT_ENVELOPE_TEMPLATE.md),
[`./WORKTREE_RUNTIME_PROTOCOL.md`](./WORKTREE_RUNTIME_PROTOCOL.md),
[`./ENVELOPE_CONSUMPTION_CHECKLIST.md`](./ENVELOPE_CONSUMPTION_CHECKLIST.md),
[`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md),
[`./ASSIGNMENT_ENVELOPE_DRY_RUN.md`](./ASSIGNMENT_ENVELOPE_DRY_RUN.md))
with minimal coherence updates to the existing delivery docs. B3
and B4 remain deferred. Live GitHub branch protection settings on
the remote repository remain a separate privileged future decision:
the landed `.github/BRANCH_PROTECTION_POLICY.md` is file-based
policy only and PR #12 did not mutate live repository settings.
With Slice E landed, the Slice E row in
[`./BACKLOG.md`](./BACKLOG.md) §c.5 is now `Done` with durable
evidence PR #14 / `3cb0266`. The structural next candidate is
Slice F shaping (release / deploy governance policy authoring), but
authorization to consume any Slice F envelope remains contingent on
Source ratifying a future privileged `deploy`-policy envelope; this
batch does not author Slice F content.

## a. Purpose

`docs/delivery/` is the **minimum repo-native delivery control plane**
for Creator Engine upstream. Its job is to let a fresh clone answer one
question after every merge:

> What is the next recommended Creator Engine task?

This is **not a Jira clone**. It is the smallest set of repo-visible
artifacts required to sequence governed work, preserve auditability
from `git clone` alone, and hand the next batch to Source for
ratification.

The control plane is markdown-only by design. Slice B1 introduced the
README, backlog, Kanban, and next-task protocol; Slice B2 layered the
Definition of Ready, Definition of Done, dependency map, and risk
register on top of that scaffold. Structured backlog sidecars and
tracker adapters remain out of scope and are deferred to later Slice
B sub-batches.

## b. Anti-Jira-clone statement

Creator Engine does not, and will not in v0.1, attempt to reimplement
an enterprise issue tracker. The delivery control plane carries only
what governance requires: a backlog of governed work items, a current
Kanban view, and a post-merge next-task protocol.

Specifically:

- This control plane does not own dashboards, notifications, sprint
  burndowns, custom workflow engines, or human-friendly board UIs.
- It does not own permissions, credentials, account configuration, or
  network-dependent state.
- It does not attempt to track every conceivable engineering task.
  Only Creator-Engine-governed work items appear here.

If a feature of an enterprise tracker is not required to answer the
next-task question or to preserve repo-native auditability, it is out
of scope. External trackers may later own those features as optional
mirrors (see §d).

## c. Source-of-truth relationship

`docs/delivery/` is a **delivery view** layered on top of, and
subordinate to, the governance and product artifacts already in the
repository. It does not redefine them.

| Upstream source of truth | Role |
|---|---|
| [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) | Apex governance authority. Conflicts resolve in favor of the constitution. |
| Feature 001 substrate (`specs/001-v0-1-governance-substrate/`, `docs/contracts/`, `schemas/`, `validators/`, `examples/`, `tenants/`) | Substrate contracts: mutation classes, authority matrix, attestation, ratification, redaction, validator. |
| Feature 002 spec (`specs/002-canonical-docs-and-operating-model/spec.md`) and the 17 canonical documents under `docs/product/`, `docs/architecture/`, `docs/governance/`, `docs/quality/`, `docs/devops/`, `docs/security/` | Operating-model contracts: SDLC state machine, Assignment Envelope schema, actor/tool ownership matrix. |
| [`docs/product/ROADMAP.md`](../product/ROADMAP.md) | Feature scope summaries and deferral rationale for Features 001–006 and v1.0. |
| [`specs/sprint-0-minimum-viable-delivery-system/README.md`](../../specs/sprint-0-minimum-viable-delivery-system/README.md) | Sprint 0 execution sequence, exit gates, and post-merge next-task protocol fields. |
| Spec Kit `tasks.md` and Creator Engine sidecars (`spec.creator-engine.yml`, `plan.creator-engine.yml`, `tasks.creator-engine.yml`) | Canonical work-item records for governed batches. |
| Optional external trackers (Jira, Linear, GitHub Projects, etc.) | **Non-canonical** mirrors only; never substitutes for repo-visible artifacts. |

Where this control plane and any upstream source of truth disagree,
the upstream source of truth wins until Source ratifies a correction.

The Feature 001 spec-status lifecycle remains the canonical lifecycle
for spec/plan/tasks artifacts. The delivery statuses used here are a
separate **delivery view** layered on top of it; see
[`./BACKLOG.md`](./BACKLOG.md) §a for the boundary.

## d. Tracker boundary

The repo-visible delivery artifacts under `docs/delivery/` are
canonical for upstream Creator Engine v0.1. The boundary is fixed:

1. Repo-visible artifacts are canonical. External tracker entries are
   **non-canonical**.
2. Jira / Linear / GitHub Projects may later be optional non-canonical
   mirrors or tenant-local adapters. They are not required.
3. External tracker IDs MAY appear as reference fields on a backlog
   item (e.g., `external_tracker_ref: ENG-1234`) but they cannot
   substitute for the repo-visible work item, the Creator Engine spec,
   the plan, the tasks, the evidence, or Source ratification.
4. A **fresh clone** of this repository, with no network access and no
   external tracker credentials, MUST be sufficient to identify the
   next recommended Creator Engine task.
5. No Jira credential, network call, board state, or external issue
   state is required for Sprint 0 exit gate #2.
6. If an external tracker entry and the repo-visible backlog disagree,
   the repo-visible backlog controls until Source ratifies an update.

This boundary aligns with
[`../architecture/SAD.md`](../architecture/SAD.md) §d, with
[`../architecture/integration-map.md`](../architecture/integration-map.md)
§d, and with
[`../../specs/sprint-0-minimum-viable-delivery-system/README.md`](../../specs/sprint-0-minimum-viable-delivery-system/README.md)
§3.

## e. File map

### B1 (present)

| File | Role |
|---|---|
| [`README.md`](./README.md) | This file. Orients the control plane, names the tracker boundary, and lists deferrals. |
| [`BACKLOG.md`](./BACKLOG.md) | Governed backlog of Sprint 0 slices and downstream features, with the delivery-view work-item row schema. |
| [`KANBAN.md`](./KANBAN.md) | Current Kanban view summarized from `BACKLOG.md`. Eight delivery-view status columns. |
| [`NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) | Post-merge completion report fields and next-task selection rules. |

### B2 (present)

| File | Role |
|---|---|
| [`DEFINITION_OF_READY.md`](./DEFINITION_OF_READY.md) | Delivery-view DoR for governed work items, layered onto Feature 001 FR-013 / FR-013a. |
| [`DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) | Delivery-view DoD, layered onto Feature 001 FR-014. |
| [`DEPENDENCIES.md`](./DEPENDENCIES.md) | Dependency map across Sprint 0 slices and downstream features. |
| [`RISK_REGISTER.md`](./RISK_REGISTER.md) | Risk register for Sprint 0 execution and immediate post-Sprint-0 work. |

### Slice E delivery docs (landed)

These five documents landed on the canonical branch under PR #14 /
commit `3cb0266 docs: add Sprint 0 Slice E assignment runtime
protocol`. They define the manual Assignment Envelope template and
worktree runtime protocol layer, authored under the Source-ratified
bounded Slice E authoring envelope (docs-only governance/delivery
content). They define the contract that any future governed
implementation envelope will obey; they do not instantiate any
automation surface, which remains Feature 005 scope under a
separately ratified privileged envelope. The Slice E row in
[`./BACKLOG.md`](./BACKLOG.md) §c.5 is `Done` on the delivery view.

| File | Role |
|---|---|
| [`ASSIGNMENT_ENVELOPE_TEMPLATE.md`](./ASSIGNMENT_ENVELOPE_TEMPLATE.md) | Reusable manual Assignment Envelope template (header, Source ratification / authority record, mutation classes, authorized actor / role / pane, allowed files / operations, prohibited surfaces, dependencies, implementation instructions, validation and scope-audit commands, review / verification evidence fields, dry-run / handoff evidence fields, explicit stop condition, distinct ratifier field). |
| [`WORKTREE_RUNTIME_PROTOCOL.md`](./WORKTREE_RUNTIME_PROTOCOL.md) | Runtime protocol for local isolated worktrees: branch / worktree naming convention; one-driver-per-worktree rule; controller / consumer split; preflight checks; no `.hermes` / handoff leakage into upstream tracked docs; no cross-project state leakage; prohibited Git / GitHub operations unless separately ratified; cleanup / defer rules. |
| [`ENVELOPE_CONSUMPTION_CHECKLIST.md`](./ENVELOPE_CONSUMPTION_CHECKLIST.md) | Consumer-side checklist for before / during / after consumption of a Source-ratified envelope. |
| [`SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md) | Independent verifier-side checklist used after the consumer reaches the stop line. |
| [`ASSIGNMENT_ENVELOPE_DRY_RUN.md`](./ASSIGNMENT_ENVELOPE_DRY_RUN.md) | Non-authorizing dry-run evidence using this Slice E worktree / branch as the worked example. |

### Slice D delivery docs (landed)

These three documents landed on the canonical branch under commit
`6058661 docs: define reviewer evidence gate for Slice D`. They
define a generic, implementation-agnostic reviewer identity
pattern, review evidence template, and review gate. They do **not**
instantiate a real reviewer identity; that work is downstream
Feature 004 scope under its own per-batch privileged envelope. The
Slice D row in [`./BACKLOG.md`](./BACKLOG.md) §c.4 is `Done` on the
delivery view.

| File | Role |
|---|---|
| [`REVIEWER_IDENTITY_REQUIREMENTS.md`](./REVIEWER_IDENTITY_REQUIREMENTS.md) | Generic reviewer identity record **pattern**. Deployment-time bindings (tool, model, host installation, durable actor, account, harness) are overlay decisions and are not selected upstream. |
| [`REVIEW_EVIDENCE_TEMPLATE.md`](./REVIEW_EVIDENCE_TEMPLATE.md) | Generic markdown-equivalent template contract for independent review evidence. Constrains `verdict` to evidence-only outcomes and states explicitly that review evidence is **not Source ratification**. |
| [`REVIEW_GATE.md`](./REVIEW_GATE.md) | Review-gate definition naming when evidence is required, how it is evaluated, what happens on blocking findings, and the standing invariants. |

Slice B is complete on the delivery view once both B1 and B2 reach
`Ratified` or `Done`. Together they satisfy Sprint 0 exit gate #2 in
full; gate #3 is satisfied by the next-task protocol authored under
B1 and cross-referenced from the B2 documents.

### Later sub-batches (deferred)

- **B3** (deferred): structured YAML backlog sidecars for work items,
  if Source later ratifies sidecar-backed backlog state.
- **B4** (deferred): optional external-tracker mirror/adapter design —
  one of Jira / Linear / GitHub Projects, including credential policy,
  conflict rules, audit evidence format, and directionality.
- Live GitHub Issues / Projects / labels / milestones mutations remain
  out of scope until separately ratified.
- Live Jira / Linear mutations remain out of scope until separately
  ratified.

## f. Out of scope for the delivery control plane

The following are out of scope for the delivery control plane and
MUST NOT be introduced as delivery-view changes under it:

- Further `.github/` workflow, PR template, branch protection policy
  file, or CODEOWNERS change beyond the file-based baseline already
  landed by `sprint-0/slice-c` (PR #12). Subsequent extension of
  that baseline (including CODEOWNERS, if and when ratified) belongs
  to its own Source-ratified `governance` envelope and ultimately to
  Feature 003.
- Live GitHub branch protection settings on the remote repository.
  The landed `.github/BRANCH_PROTECTION_POLICY.md` is file-based
  policy only; the live repository setting remains a separate
  privileged future decision and is not authorized by Slice C
  landing.
- Any change to `specs/`, `schemas/`, `validators/`, `templates/`,
  `examples/`, `tenants/`, `docs/product/`, `docs/architecture/`,
  `docs/governance/`, `docs/quality/`, `docs/devops/`,
  `docs/security/`, or `docs/contracts/`.
- Any structured YAML backlog sidecar (deferred to B3 / B4).
- Any external-tracker integration, credential, or network call.
- Any live GitHub or external-tracker mutation.
- Implementation of US3 A1 (not authorized).
- Implementation of any Slice F work (which requires its own
  Source-ratified privileged envelope per Feature 001 FR-008 /
  FR-016 before any consumption begins). Slice D landed on the
  canonical branch (commit `6058661`) and Slice E has now landed
  (PR #14 / commit `3cb0266`); the structural next candidate is
  Slice F shaping (release / deploy governance policy authoring)
  under a future Source-ratified privileged envelope, and final
  next-task selection remains Source's.

## g. How this control plane is used

After every merge to the canonical branch:

1. The merge author / Hermes runs the post-merge completion report
   per [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md).
2. [`./BACKLOG.md`](./BACKLOG.md) and [`./KANBAN.md`](./KANBAN.md) are
   updated to reflect the new state (status transitions, new items if
   ratified).
3. The completion report names the immediate next-task recommendation,
   selected per the rules in
   [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §c.
4. Source ratifies the next-task recommendation before any new
   Assignment Envelope is authored.

A merge report that does not name the next task is incomplete per
[`../../specs/sprint-0-minimum-viable-delivery-system/README.md`](../../specs/sprint-0-minimum-viable-delivery-system/README.md)
§7.

## h. Acceptance posture for B1 and B2

This README satisfies the B1 envelope's README requirements and is
extended to discover the B2 documents:

- Names the purpose as the minimum repo-native delivery control plane.
- States explicitly that this is not a Jira clone.
- Names the source-of-truth relationship with the constitution,
  Feature 001 substrate, Feature 002 operating model, the roadmap,
  the Sprint 0 execution README, Spec Kit `tasks.md`, Creator Engine
  sidecars, and optional external trackers.
- Provides the file map for the present B1 and B2 files and the
  deferred B3 / B4 files.
- States that a fresh clone is sufficient to identify the next task
  and that no external tracker credential or network state is required
  for Sprint 0 exit gate #2.
- Enumerates the out-of-scope surfaces for the original B1 and B2
  acceptance posture (the §f rewrite post-PR #12 carries the
  current delivery-view scope statement).
