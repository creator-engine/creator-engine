# Creator Engine Kanban

**Status**: Sprint 0 Slice B1 scaffold. Generated from / summarizes
[`./BACKLOG.md`](./BACKLOG.md).

This board is part of the **minimum repo-native delivery control
plane** and is **not a Jira clone**. It is a current readable view
over the canonical backlog. The backlog rows in `BACKLOG.md` are the
source of truth; if a row appears here and not there (or vice versa),
the backlog wins until reconciled. A fresh clone is sufficient to read
this board; no external tracker credential or network state is
required.

## a. Columns

| Column | Delivery-view semantics |
|---|---|
| `Backlog` | Identified work, not yet selected or shaped enough to start. |
| `Ready` | Shaped, dependencies satisfied, eligible to enter an envelope. |
| `In Progress` | Inside an active Assignment Envelope, before independent verification completes. |
| `Verified` | Local validation and independent review evidence recorded; awaiting ratification. |
| `Ratified` | Source ratification recorded; merge authorized but not finalized (or finalized but post-merge evidence incomplete). |
| `Done` | Merged on the canonical branch with finalized attestation. |
| `Deferred` | Intentionally not in scope for the current sprint, with a named owning future slice or feature. |
| `Blocked` | Cannot advance until a named blocker clears; the blocker is the implied next task. |

Delivery-view statuses are layered on top of, and do not amend, the
Feature 001 spec-status lifecycle (`draft → ready → in_progress →
verified → ratified → done`, FR-013a). See
[`./BACKLOG.md`](./BACKLOG.md) §a.

## b. Current board

Last derived from the backlog as recorded in this batch. After every
merge, this board is regenerated per
[`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b.

### Backlog

*(No items currently shaped only at `Backlog`. New items first land
here before being promoted to `Ready`.)*

### Ready

*(No items currently in this column. `sprint-0/slice-b/b2` is the
expected occupant once `sprint-0/slice-b/b1` reaches `Ratified` or
`Done`; until then B2 is `Blocked` (see §Blocked and §c).)*

### In Progress

| id | scope (one line) | envelope class | notes |
|---|---|---|---|
| `sprint-0/slice-b/b1` | Create `docs/delivery/README.md`, `BACKLOG.md`, `KANBAN.md`, `NEXT_TASK_PROTOCOL.md` under a Source-ratified envelope-equivalent; markdown-only. | `docs` | Current batch. Will move to `Verified` once the envelope's required validation passes. |
| `sprint-0/slice-b` | Establish the minimum repo-native delivery control plane (covers B1 and B2). | `docs` | Parent slice; tracks B1 and B2 progress. |

### Verified

*(No items currently in this column.)*

### Ratified

*(No items currently in this column. Items land here after Source
ratification but before the post-merge attestation is finalized in
§Done.)*

### Done

| id | scope (one line) | durable evidence |
|---|---|---|
| `feature-001` | v0.1 governance substrate: identity, attestation, mutation classes, authority matrix, DoR/DoD, ratification flow, redaction gate, validator, dogfood tenant fixture, examples, verification spec. | Merged under `specs/001-v0-1-governance-substrate/` and substrate artifacts under `docs/contracts/`, `schemas/`, `validators/`, `examples/`, `tenants/`. |
| `feature-002` | v0.1-docs operating-model spec (specification-only at the operating-model layer). | Merged spec at `specs/002-canonical-docs-and-operating-model/spec.md`. |
| `sprint-0/slice-a` | Author the 17 Feature 002 canonical documents under `docs/product/`, `docs/architecture/`, `docs/governance/`, `docs/quality/`, `docs/devops/`, `docs/security/`. | Canonical-branch commits `51a885e docs: integrate Sprint 0 Slice A canonical docs (#5)` and `7cc082f docs: harden Slice A post-merge references (#6)`. |

### Deferred

| id | scope (one line) | owning future slice / feature |
|---|---|---|
| `sprint-0/slice-b/b3` | Structured YAML backlog sidecars for work items. | `sprint-0/slice-b` (later sub-batch). |
| `sprint-0/slice-b/b4` | Optional external-tracker mirror/adapter design (Jira / Linear / GitHub Projects), non-canonical. | `sprint-0/slice-b` (later sub-batch). |
| `feature-003` | GitHub CI governance (workflows, PR template, branch protection, review policy). | Sprint 0 Slice C policy outline → Feature 003 spec. |
| `feature-004` | Independent review / QA / security identities and evidence schemas. | Sprint 0 Slice D outline → Feature 004 spec. |
| `feature-005` | Hermes dispatcher, worktree lifecycle automation, sandboxing, safe parallel runtime. | Sprint 0 Slice E protocol → Feature 005 spec. |
| `feature-006` | Release / deployment governance; release agent identity; deploy attestations; rollback evidence; GitHub environments. | Sprint 0 Slice F policy → Feature 006 spec. |
| `v1.0` | End-to-end governed agentic SDLC integration target. | Sprint 0 exit + Features 003–006 ratified. |
| `us3/a1` | Reserved item; implementation not authorized. | Awaits explicit Source ratification of a future spec. |

### Blocked

| id | scope (one line) | named blocker |
|---|---|---|
| `sprint-0/slice-b/b2` | Author `DEFINITION_OF_READY.md`, `DEFINITION_OF_DONE.md`, `DEPENDENCIES.md`, and `RISK_REGISTER.md` under `docs/delivery/`. | `sprint-0/slice-b/b1` must reach `Ratified` or `Done`; B1 is currently `In Progress` under this batch. |
| `sprint-0/slice-c` | Thin GitHub / CI / PR governance (workflows, PR template, branch protection policy, review policy). | `sprint-0/slice-b` not yet complete; Slice C mutations require per-batch Source ratification (privileged). |
| `sprint-0/slice-d` | Minimum review / QA / identity governance (Codex review identity, QA / review evidence template, review gate). | `sprint-0/slice-c` not yet complete; Slice D includes privileged `identity` work. |
| `sprint-0/slice-e` | Manual Assignment Envelope template + worktree/branch naming + one-driver-per-worktree rule + envelope dry-run evidence. | `sprint-0/slice-c` and `sprint-0/slice-d` not yet complete. |
| `sprint-0/slice-f` | Release / deploy governance policy; deploy mutation ratification rule; release-candidate / merge-approval / deployment-approval checklists. | `sprint-0/slice-e` not yet complete; deploy targets do not yet exist. |

## c. Immediate next likely post-B1 task

`sprint-0/slice-b/b2` is currently `Blocked` (see §Blocked) because
its named dependency `sprint-0/slice-b/b1` has not yet reached
`Ratified` or `Done`. Subject to Source ratification of this batch,
which advances B1 to `Ratified` and clears that dependency, the
immediate next post-B1 task is:

> **`sprint-0/slice-b/b2`** — author the deferred B2 documents
> (`DEFINITION_OF_READY.md`, `DEFINITION_OF_DONE.md`,
> `DEPENDENCIES.md`, `RISK_REGISTER.md`) under `docs/delivery/`.

Rationale: B2 is the highest-priority `Blocked` item, its only
dependency is `sprint-0/slice-b/b1` reaching `Ratified`, and Sprint 0
exit gate #2 cannot be fully satisfied until B2 lands. Per
[`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §c.4, the named
blocking dependency (B1 ratification) is the implied next task until
it clears; once cleared, B2 becomes the highest-priority `Ready`
candidate per §c.1. Slice C is gated on Slice B reaching `Ratified`
or `Done`, so B2 is also the shortest path to unblock the next
privileged slice.

If validation or review of B1 surfaces a blocker, the next-task
recommendation defers to the rules in
[`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §c. Per those
rules, a named blocker becomes the implied next task; a missing or
ambiguous backlog state escalates to Source.

## d. Board hygiene rules

1. The board is regenerated from `BACKLOG.md` after every merge. The
   backlog row is the source of truth; the board row is a view.
2. A board row MUST cite the corresponding backlog id. Boards do not
   introduce new ids.
3. The Kanban view MUST NOT amend the Feature 001 spec-status
   lifecycle. A board status applies to the delivery item, not to the
   underlying spec/plan/tasks lifecycle.
4. Instance-local facts (absolute filesystem paths, terminal
   identifiers, in-flight PR numbers, local session queues, secrets,
   tokens) MUST NOT appear here. Merged PR numbers in commit subjects
   MAY be cited as historical evidence.
5. External tracker columns, swimlanes, or labels MUST NOT be
   introduced under B1. If a future ratified adapter (B4) needs
   tracker visibility, it will be designed as a non-canonical mirror
   per [`./README.md`](./README.md) §d.
