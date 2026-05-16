# Creator Engine Kanban

**Status**: Sprint 0 Slices B, C, D, E, and F are complete on the
delivery view. B1 (markdown control-plane scaffold) and B2
(Definition of Ready, Definition of Done, dependency map, risk
register) landed previously; Slice C subsequently landed on the
canonical branch as PR #12 (`1cfb955 ci: add baseline governance
validation controls`), introducing the file-based `.github/`
baseline (validation workflow, PR template, branch protection
policy file); Slice D has since landed on the canonical branch
as commit `6058661 docs: define reviewer evidence gate for Slice D`,
landing the three Slice D delivery docs and minimal coherence
updates; Slice E subsequently landed on the canonical branch as
PR #14 / commit `3cb0266 docs: add Sprint 0 Slice E assignment
runtime protocol`, landing the five Slice E delivery docs and
minimal coherence updates; and Slice F has now landed on the
canonical branch as PR #16 / commit `cb7f94a docs: add Slice F
release deploy governance policy`, landing the five Slice F
delivery docs and minimal coherence updates. Live GitHub branch
protection settings on the remote repository remain a separate
privileged future decision and are not mutated by PR #12, PR #14,
or PR #16. The canonical Slice F row has moved from `Blocked` to
`Done` on the board below with durable evidence PR #16 / `cb7f94a`.
Post-Sprint-0 substrate has since landed and is reflected in the
`Done` table below: `post-sprint-0/oss-readiness` (PR #20 / `35bf85f`
and PR #21 / `5b762f9`) and `post-sprint-0/workflow-hardening`
(PR #22 / `d892cd3` and PR #23 / `3dc45a1`). CFC-1
(`post-sprint-0/cfc-1-codex-first-class`) governance scope and
operations protocol substrate has landed on the canonical branch as
PR #25 / `30a3e8c` and has moved from `Backlog` to `Done` on the
board below; see [`./BACKLOG.md`](./BACKLOG.md) §e.10.
Generated from / summarizes [`./BACKLOG.md`](./BACKLOG.md).

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

| id | scope (one line) | dependencies / blockers |
|---|---|---|
| `post-sprint-0/cfc-2a-codex-role-decision` | CFC follow-on Batch 2A decision-request artifact (`docs/governance/CODEX_ROLE_AND_AUTHORITY_DECISION.md`) letting Source decide Codex `role_category`, allowed mutation classes, authority boundary, binding posture, review-evidence semantics, public/tenant role label, and reaffirmation that `docs/contracts/authority-matrix.yml` is not mutated by Batch 2A. `governance` / `docs` mutation class. | `post-sprint-0/cfc-1-codex-first-class` (`Done`, PR #25 / `30a3e8c`). |

### Ready

*(No items currently shaped only at `Ready`. `sprint-0/slice-d`,
`sprint-0/slice-e`, and `sprint-0/slice-f` have all landed on the
canonical branch; see the `Done` table below.)*

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
| `sprint-0/slice-d` | Generic reviewer identity record **pattern** (not an instantiated identity); generic markdown-equivalent QA / review evidence template; review-gate definition; standing invariant that review evidence is not Source ratification. | Canonical-branch commit `6058661 docs: define reviewer evidence gate for Slice D` landed `docs/delivery/REVIEWER_IDENTITY_REQUIREMENTS.md`, `docs/delivery/REVIEW_EVIDENCE_TEMPLATE.md`, and `docs/delivery/REVIEW_GATE.md`, with minimal coherence updates to `docs/delivery/README.md`, `docs/delivery/BACKLOG.md`, this Kanban, and `docs/delivery/DEPENDENCIES.md`. |
| `sprint-0/slice-e` | Manual Assignment Envelope template; worktree / branch naming and one-driver-per-worktree rule; envelope consumption and scope-audit checklists; non-authorizing dry-run evidence. | Canonical-branch commit `3cb0266 docs: add Sprint 0 Slice E assignment runtime protocol (#14)` landed `docs/delivery/ASSIGNMENT_ENVELOPE_TEMPLATE.md`, `docs/delivery/WORKTREE_RUNTIME_PROTOCOL.md`, `docs/delivery/ENVELOPE_CONSUMPTION_CHECKLIST.md`, `docs/delivery/SCOPE_AUDIT_CHECKLIST.md`, and `docs/delivery/ASSIGNMENT_ENVELOPE_DRY_RUN.md`, with minimal coherence updates to `docs/delivery/README.md`, `docs/delivery/BACKLOG.md`, this Kanban, and `docs/delivery/DEPENDENCIES.md`. |
| `sprint-0/slice-f` | Release-candidate checklist; merge-approval checklist; deployment-approval policy; rollback / evidence expectations; explicit `deploy` mutation ratification rule; statement of currently absent deployment targets / environments. Policy / docs only; not deploy automation. | Canonical-branch commit `cb7f94a docs: add Slice F release deploy governance policy (#16)` landed `docs/delivery/RELEASE_DEPLOY_GOVERNANCE.md`, `docs/delivery/RELEASE_CANDIDATE_CHECKLIST.md`, `docs/delivery/MERGE_APPROVAL_CHECKLIST.md`, `docs/delivery/DEPLOYMENT_APPROVAL_POLICY.md`, and `docs/delivery/ROLLBACK_AND_POST_RELEASE_EVIDENCE.md`, with minimal coherence updates to existing delivery docs. |
| `post-sprint-0/oss-readiness` | Open-source readiness materials (PR #20) and public-launch readiness blocker remediation (PR #21). Post-Sprint-0 substrate; not a Sprint 0 Slice A-F item. | Canonical-branch commits `35bf85f docs: add open-source readiness materials (#20)` and `5b762f9 fix: remediate public launch readiness blockers (#21)`. |
| `post-sprint-0/workflow-hardening` | Workflow-hardening protocol set: operations protocol docs, schemas, templates, validator checks, CI validator hardening. Durable evidence for R-011 and R-012. Post-Sprint-0 substrate; not a Sprint 0 Slice A-F item. | Canonical-branch commits `d892cd3 feat: add workflow hardening controls (#22)` and `3dc45a1 fix: harden workflow validator follow-ups (#23)`. |
| `post-sprint-0/cfc-1-codex-first-class` | Governance scope + operations protocol substrate for Codex-first-class, without identity instantiation, schema mutation, authority expansion, provider binding, GitHub settings mutation, or Feature 005 dispatch automation. Batch 2+ deferred to separately Source-ratified envelopes. | Canonical-branch commit `30a3e8c docs: add CFC-1 scope and protocol envelope (#25)`. |

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

*(No items currently in this column. `sprint-0/slice-f` has landed
on the canonical branch; see the `Done` table above.)*

## c. Immediate next likely task

CFC-1 (`post-sprint-0/cfc-1-codex-first-class`) governance scope
and operations protocol substrate has landed on the canonical branch
as PR #25 / `30a3e8c`. All Sprint 0 Slices A–F and post-Sprint-0
substrate items (`post-sprint-0/oss-readiness`, `Done`;
`post-sprint-0/workflow-hardening`, `Done`; and now
`post-sprint-0/cfc-1-codex-first-class`, `Done`) are complete on
the delivery view.

There are no items currently in `Backlog`, `Ready`, `In Progress`,
`Verified`, or `Ratified`. The next work is a separate
Source-ratified follow-on selection. No next task is mechanically
certain from the current delivery state; final next-task selection
remains Source's.

> All Sprint 0 slices and post-Sprint-0 substrate items have landed
> on the canonical branch. Downstream deferred candidates (Feature
> 003 extension of the landed `.github/` baseline, Feature 004
> reviewer-identity instantiation / CFC follow-on Batch 2+, Feature
> 005 dispatcher / worktree automation, Feature 006 release / deploy
> execution) are each `Deferred` in
> [`./BACKLOG.md`](./BACKLOG.md) §e and require their own
> Source-ratified privileged envelopes per Feature 001 FR-008 /
> FR-016. Final next-task selection — including which feature
> shaping is in fact next, and under what bounded envelope —
> remains Source's.

If the next-task selection surfaces ambiguity, the recommendation
defers to the rules in
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
