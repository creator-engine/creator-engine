# Creator Engine Kanban

**Status**: Sprint 0 Slices B and C are complete on the delivery
view. B1 (markdown control-plane scaffold) and B2 (Definition of
Ready, Definition of Done, dependency map, risk register) landed
previously; Slice C has since landed on the canonical branch as
PR #12 (`1cfb955 ci: add baseline governance validation controls`),
introducing the file-based `.github/` baseline (validation workflow,
PR template, branch protection policy file). Live GitHub branch
protection settings on the remote repository remain a separate
privileged future decision and are not mutated by PR #12.
`sprint-0/slice-d` is the next candidate envelope; its
implementation is not authorized by this state and requires its own
Source-ratified privileged envelope. Generated from / summarizes
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

| id | scope (one line) | envelope class | notes |
|---|---|---|---|
| `sprint-0/slice-d` | Codex reviewer identity record (or equivalent); QA / review evidence template; review gate definition; rule that review evidence is not Source ratification. | `identity` (privileged) | Delivery-view dependency on Slice C is cleared (`sprint-0/slice-c` is `Done`, see Done row below). Slice D is the next candidate envelope. Implementation does NOT begin under this reconciliation — Slice D requires its own Source-ratified privileged envelope per Feature 001 FR-008 / FR-016 before promotion to `In Progress`. |

### In Progress

*(No items currently in this column.)*

### Verified

*(No items currently in this column.)*

### Ratified

*(No items currently in this column.)*

### Done

| id | scope (one line) | durable evidence |
|---|---|---|
| `feature-001` | v0.1 governance substrate: identity, attestation, mutation classes, authority matrix, DoR/DoD, ratification flow, redaction gate, validator, dogfood tenant fixture, examples, verification spec. | Merged under `specs/001-v0-1-governance-substrate/` and substrate artifacts under `docs/contracts/`, `schemas/`, `validators/`, `examples/`, `tenants/`. |
| `feature-002` | v0.1-docs operating-model spec (specification-only at the operating-model layer). | Merged spec at `specs/002-canonical-docs-and-operating-model/spec.md`. |
| `sprint-0/slice-a` | Author the 17 Feature 002 canonical documents under `docs/product/`, `docs/architecture/`, `docs/governance/`, `docs/quality/`, `docs/devops/`, `docs/security/`. | Canonical-branch commits `51a885e docs: integrate Sprint 0 Slice A canonical docs (#5)` and `7cc082f docs: harden Slice A post-merge references (#6)`. |
| `sprint-0/slice-b` | Establish the minimum repo-native delivery control plane (covers B1 and B2). | Slice B is complete on the delivery view: B1 and B2 have both landed on the canonical branch (see rows below). |
| `sprint-0/slice-b/b1` | Create `docs/delivery/README.md`, `BACKLOG.md`, `KANBAN.md`, `NEXT_TASK_PROTOCOL.md` under a Source-ratified envelope-equivalent; markdown-only. | Canonical-branch commit `77e0bfe docs: add Sprint 0 Slice B1 delivery control plane (#7)`. |
| `sprint-0/slice-b/b2` | Author `DEFINITION_OF_READY.md`, `DEFINITION_OF_DONE.md`, `DEPENDENCIES.md`, and `RISK_REGISTER.md` under `docs/delivery/`, with minimal coherence updates to the B1 docs. | Canonical-branch commit `d4a2636 docs: add Sprint 0 Slice B2 readiness controls (#10)`. |
| `sprint-0/slice-c` | Thin GitHub / CI / PR governance baseline: validation workflow, PR template, and branch protection policy file under `.github/`. Live GitHub branch protection settings on the remote repository remain a separate privileged future decision and were not mutated. | Canonical-branch commit `1cfb955 ci: add baseline governance validation controls (#12)` landed `.github/workflows/validate.yml`, `.github/pull_request_template.md`, and `.github/BRANCH_PROTECTION_POLICY.md`. |

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
| `sprint-0/slice-e` | Manual Assignment Envelope template + worktree/branch naming + one-driver-per-worktree rule + envelope dry-run evidence. | `sprint-0/slice-d` not yet complete. |
| `sprint-0/slice-f` | Release / deploy governance policy; deploy mutation ratification rule; release-candidate / merge-approval / deployment-approval checklists. | `sprint-0/slice-e` not yet complete; deploy targets do not yet exist. |

## c. Immediate next likely task

With `sprint-0/slice-c` `Done` on the delivery view (PR #12 landed
the file-based `.github/` baseline), Slice D is no longer
delivery-view `Blocked` on Slice C; it has been promoted to `Ready`
as the next candidate envelope.

> **The immediate next task is `sprint-0/slice-d`** — author the
> Codex reviewer identity record (or equivalent), the QA / review
> evidence template, and the review-gate definition (Sprint 0 exit
> gates #7 and #10). Slice D is `Ready` (highest-priority `Ready`
> item per [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §c.1)
> but Slice D mutations are privileged (`identity`), so the next
> governed action is a **ratification request to Source** for a
> Slice D privileged envelope per Feature 001 FR-008 / FR-016 and
> per [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §c.5.
> Slice D implementation does not begin until that envelope is
> ratified. Slice D consumption requirements remain governed by
> [`./DEFINITION_OF_READY.md`](./DEFINITION_OF_READY.md) §c.

Rationale: Slice D is gated on Slice C reaching `Ratified` or `Done`
per [`./DEPENDENCIES.md`](./DEPENDENCIES.md) §b. With Slice C `Done`,
Slice D is the highest-priority backlog candidate. Because Slice D
crosses privileged surfaces, the §c.5 routing — privileged blocker
becomes a ratification request rather than an implementation task —
applies. Note: any extension of the landed `.github/` baseline
(including CODEOWNERS, live branch protection settings, or
Feature 003 instantiation) is itself a separate privileged
envelope and is not unblocked by Slice C landing.

If shaping or scoping of the Slice D envelope surfaces ambiguity,
the next-task recommendation defers to the rules in
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
