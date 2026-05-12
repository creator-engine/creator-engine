# Creator Engine Delivery Control Plane

**Status**: Sprint 0 Slice B1 scaffold. Source-ratified posture under
Option C of the Slice B strategy decision. Awaiting downstream Slice B2
expansion before Slice B is complete.

## a. Purpose

`docs/delivery/` is the **minimum repo-native delivery control plane**
for Creator Engine upstream. Its job is to let a fresh clone answer one
question after every merge:

> What is the next recommended Creator Engine task?

This is **not a Jira clone**. It is the smallest set of repo-visible
artifacts required to sequence governed work, preserve auditability
from `git clone` alone, and hand the next batch to Source for
ratification.

The control plane is markdown-only in B1 by design. Structured backlog
sidecars, dependency graphs, risk registers, and tracker adapters are
out of scope for B1 and are deferred to later Slice B sub-batches.

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

### B1 (this batch — present)

| File | Role |
|---|---|
| [`README.md`](./README.md) | This file. Orients the control plane, names the tracker boundary, and lists deferrals. |
| [`BACKLOG.md`](./BACKLOG.md) | Governed backlog of Sprint 0 slices and downstream features, with work-item fields sufficient for B1. |
| [`KANBAN.md`](./KANBAN.md) | Current Kanban view summarized from `BACKLOG.md`. Eight delivery-view status columns. |
| [`NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) | Post-merge completion report fields and next-task selection rules. |

### B2 (deferred — absent in this batch)

| File | Role |
|---|---|
| `docs/delivery/DEFINITION_OF_READY.md` | Delivery-view DoR for governed work items, layered onto Feature 001 FR-013 / FR-013a. |
| `docs/delivery/DEFINITION_OF_DONE.md` | Delivery-view DoD, layered onto Feature 001 FR-014. |
| `docs/delivery/DEPENDENCIES.md` | Dependency map across Sprint 0 slices and downstream features. |
| `docs/delivery/RISK_REGISTER.md` | Risk register for Sprint 0 execution and immediate post-Sprint-0 work. |

Slice B is not complete until B2 lands. B1 alone does not satisfy
Sprint 0 exit gate #2 in full.

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

## f. Out of scope for B1

The following are explicitly out of scope for this batch and MUST NOT
be introduced under it:

- Any `.github/` workflow, PR template, branch protection setting, or
  CODEOWNERS change (Feature 003 / Sprint 0 Slice C).
- Any change to `specs/`, `schemas/`, `validators/`, `templates/`,
  `examples/`, `tenants/`, `docs/product/`, `docs/architecture/`,
  `docs/governance/`, `docs/quality/`, `docs/devops/`,
  `docs/security/`, or `docs/contracts/`.
- Any structured YAML backlog sidecar (deferred to B3 / B4).
- Any external-tracker integration, credential, or network call.
- Any live GitHub or external-tracker mutation.
- Implementation of US3 A1 (not authorized).
- Implementation of Slice B2 work (deferred to its own ratified batch).

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

## h. Acceptance posture for B1

This README satisfies the B1 envelope's README requirements:

- Names the purpose as the minimum repo-native delivery control plane.
- States explicitly that this is not a Jira clone.
- Names the source-of-truth relationship with the constitution,
  Feature 001 substrate, Feature 002 operating model, the roadmap,
  the Sprint 0 execution README, Spec Kit `tasks.md`, Creator Engine
  sidecars, and optional external trackers.
- Provides the file map for B1 and the deferred B2 / B3 / B4 files.
- States that a fresh clone is sufficient to identify the next task
  and that no external tracker credential or network state is required
  for Sprint 0 exit gate #2.
- Enumerates the out-of-scope surfaces for the B1 batch.
