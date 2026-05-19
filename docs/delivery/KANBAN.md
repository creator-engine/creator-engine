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
board below; see [`./BACKLOG.md`](./BACKLOG.md) §e.10. CFC follow-on
Batch 2A (`post-sprint-0/cfc-2a-codex-role-decision`) has landed on
the canonical branch as PR #27 / `6b51882 docs: draft Codex role
authority decision (#27)` and has moved from `Backlog` to `Done` on
the board below; see [`./BACKLOG.md`](./BACKLOG.md) §e.11. CFC
follow-on Batch 2B (`post-sprint-0/cfc-2b-codex-architecture-matrix`)
has landed on the canonical branch as PR #28 / `c06a3e7 docs: encode
Codex architecture matrix role decision` and is `Done` on the board
below; see [`./BACKLOG.md`](./BACKLOG.md) §e.12. CFC follow-on Batch
2C (`post-sprint-0/cfc-2c-codex-identity-decision`) has landed on
the canonical branch as PR #29 / `66a8074 docs: draft Codex identity
record encoding decision (#29)` and is `Done` on the board below;
see [`./BACKLOG.md`](./BACKLOG.md) §e.13. Source ratified eight §6
decisions. The Codex identity record authoring envelope
(`post-sprint-0/cfc-codex-identity-record-authoring`) has since
landed on the canonical branch as PR #31 / merge commit `78b57a4
docs: author Codex identity record (#31)` and is `Done` on the
board below; see [`./BACKLOG.md`](./BACKLOG.md) §e.14. CFC follow-on
Batch 2D.1 review-evidence schema
(`post-sprint-0/cfc-2d-1-review-evidence-schema`) has since landed on
the canonical branch as PR #34 / merge commit `e1f5ffc feat: add
review evidence schema contract (#34)` (PR head SHA `2a8fe0f`) and
is `Done` on the board below; see
[`./BACKLOG.md`](./BACKLOG.md) §e.15. CFC follow-on Batch 2D.2
architect-evidence schema
(`post-sprint-0/cfc-2d-2-architect-evidence-schema`) has since
landed on the canonical branch as PR #36 / merge commit `51a2134
feat: add architect evidence schema contract (#36)` (PR head SHA
`451be39`) and is `Done` on the board below; see
[`./BACKLOG.md`](./BACKLOG.md) §e.16. CFC follow-on Batch 2D.3
implementer-evidence schema
(`post-sprint-0/cfc-2d-3-implementer-evidence-schema`) has since
landed on the canonical branch as PR #38 / merge commit `01f21a5
feat: add implementer evidence schema contract (#38)` (PR head SHA
`0b630be`) and is `Done` on the board below; see
[`./BACKLOG.md`](./BACKLOG.md) §e.17. Gate 2 Lane A
(`post-sprint-0/gate-2-lane-a-parallel-pair-rehearsal-runbook`) has
since landed on the canonical branch as PR #40 / merge commit `a63304a
docs: add parallel pair rehearsal runbook (#40)` and is `Done` on the
board below; see [`./BACKLOG.md`](./BACKLOG.md) §e.18.
`docs/operations/PARALLEL_PAIR_REHEARSAL_RUNBOOK.md` is
operational/non-normative; public visibility remains separately gated.
Gate 2 Lane B
(`post-sprint-0/gate-2-lane-b-external-contributor-intake-boundary`)
has since landed on the canonical branch as PR #41 / merge commit
`8dd18a0 docs: add external contributor intake boundary (#41)` and is
`Done` on the board below; see [`./BACKLOG.md`](./BACKLOG.md) §e.19.
The post-Sprint-0 substrate parent
`post-sprint-0/root-worktree-lifecycle` has since landed on the
canonical branch as PR #44 / merge commit `30327aa docs: add root
worktree invariant policy (#44)`; the parent row and the
`post-sprint-0/root-worktree-lifecycle/policy-docs-current` child are
now `Done` on the board below alongside the previously-`Done`
`post-sprint-0/root-worktree-lifecycle/audit` child, while
`post-sprint-0/root-worktree-lifecycle/checks-preflight` and
`post-sprint-0/root-worktree-lifecycle/current-root-reconciliation`
remain `Deferred`; see [`./BACKLOG.md`](./BACKLOG.md) §e.20.
Public-readiness continuation remains separately Source-ratified and
unimplemented; the deferred checks/preflight and current-root
reconciliation gates are explicitly later gates and are not on the
public-readiness critical path. The post-Sprint-0 substrate parent `post-sprint-0/public-readiness`
and its `post-sprint-0/public-readiness/gate-artifact` child have
landed on the canonical branch as PR #46 / merge commit `2ee63ddde7608c1bb7c9dc52dab2eadb097d2233
docs: add public readiness continuation gate (#46)` and are now
`Done` on the board below; the
`post-sprint-0/public-readiness/visibility-flip` child remains
`Deferred` as the named owning future privileged envelope for the
actual repository visibility flip; see
[`./BACKLOG.md`](./BACKLOG.md) §e.21.
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

*(No items currently in this column. The Codex identity record authoring
envelope has landed (PR #31 / `78b57a4`), Batch 2D.1 review-evidence
schema has landed (PR #34 / `e1f5ffc`, head `2a8fe0f`), Batch 2D.2
architect-evidence schema has landed (PR #36 / `51a2134`, head
`451be39`), Batch 2D.3 implementer-evidence schema has landed
(PR #38 / `01f21a5`, head `0b630be`), Gate 2 Lane A has landed
(PR #40 / `a63304a`), and Gate 2 Lane B has landed (PR #41 /
`8dd18a0`); see `Done` table below and
[`./BACKLOG.md`](./BACKLOG.md) §e.18–§e.19.)*

### Ready

*(No items currently shaped only at `Ready`. `sprint-0/slice-d`,
`sprint-0/slice-e`, and `sprint-0/slice-f` have all landed on the
canonical branch; see the `Done` table below.)*

### In Progress

*(No items currently in this column. `post-sprint-0/public-readiness`
and `post-sprint-0/public-readiness/gate-artifact` have landed
(PR #46 / `2ee63dd`); see `Done` table below and
[`./BACKLOG.md`](./BACKLOG.md) §e.21–§e.21.1.)*

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
| `post-sprint-0/cfc-2a-codex-role-decision` | CFC follow-on Batch 2A Codex role/authority decision request at `docs/governance/CODEX_ROLE_AND_AUTHORITY_DECISION.md`. Source ratified Option C (per-batch architect/implementer authoring assignment); Phase-1 allowed mutation classes = `governance`, `docs`, and `code` (with `code` gated to implementer-class envelopes; privileged classes Source-ratified); provider/tool/model/host/account binding remains placeholder/unbound; review evidence retained as a separate artifact class; `codex-architect` is a tenant/public overlay alias only; `docs/contracts/authority-matrix.yml` not mutated. | Canonical-branch commit `6b51882 docs: draft Codex role authority decision (#27)`. |
| `post-sprint-0/cfc-2b-codex-architecture-matrix` | CFC follow-on Batch 2B architecture actor/tool matrix update at `docs/architecture/agent-interaction-model.md` §a (Codex row) and §b.4 (per-batch governed authoring / review pattern). Instantiates Batch 2A §6.1 Option C; authority remains envelope-bound, not personality-bound; Codex retains authoring parity only — no ratification, merge, or deploy authority; `codex-architect` named as tenant/public overlay alias, not a new baseline `role_category` row. `governance` / `docs` mutation class only — identity record, evidence schemas, authority matrix, and provider binding remain deferred. | Canonical-branch commit `c06a3e7 docs: encode Codex architecture matrix role decision` (PR #28). |
| `post-sprint-0/cfc-2c-codex-identity-decision` | CFC follow-on Batch 2C identity record encoding decision at `docs/governance/CODEX_IDENTITY_RECORD_ENCODING_DECISION.md`. Source ratified eight §6 decisions: Option A (single record, `role_category = architect`; Option C conservative fallback retained); `human_ratifier_roles = ["source"]`; placeholder/unbound posture for `allowed_repositories`, `signing_policy`, storage paths, and `tenant_id`; Batch 2D reaffirmed as downstream. `governance` / `docs` mutation class only — identity record, schemas, authority matrix, validators, templates, examples, tenants, `docs/architecture/**`, and `.github/**` not mutated. | Canonical-branch commit `66a8074 docs: draft Codex identity record encoding decision (#29)`. |
| `post-sprint-0/cfc-codex-identity-record-authoring` | CFC follow-on Codex identity record authoring: single Codex identity record with `role_category = architect`, `human_ratifier_roles = ["source"]`, placeholder/unbound posture for `allowed_repositories`, `signing_policy`, and `tenant_id`; storage paths under `tenants/creator-engine-substrate/codex/`; no concrete provider/tool/model/host/account binding; no schema, contract, or architecture file modified; Codex authority not expanded; Batch 2D remains a separate downstream gate. | Canonical-branch commit `78b57a4 docs: author Codex identity record (#31)`. |
| `post-sprint-0/cfc-2d-1-review-evidence-schema` | CFC follow-on Batch 2D.1 conservative machine-readable lift of [`./REVIEW_EVIDENCE_TEMPLATE.md`](./REVIEW_EVIDENCE_TEMPLATE.md): `schemas/review-evidence.schema.yaml`, `templates/review-evidence.template.yaml`, `docs/contracts/review-evidence.md`, `review_evidence_schema` validator check with unit/integration tests, well-formed and malformed examples, and minimal coherence updates to the prose template status pointer, the contracts README, this Kanban, [`./BACKLOG.md`](./BACKLOG.md) §e.15, and [`./DEPENDENCIES.md`](./DEPENDENCIES.md). Sibling architect-evidence (Batch 2D.2) has since landed (see the row below and [`./BACKLOG.md`](./BACKLOG.md) §e.16); implementer-evidence (Batch 2D.3) schema remains downstream. | Canonical-branch merge commit `e1f5ffc feat: add review evidence schema contract (#34)` (PR head SHA `2a8fe0f`). |
| `post-sprint-0/cfc-2d-2-architect-evidence-schema` | CFC follow-on Batch 2D.2 conservative machine-readable schema-class authoring slice for governed architect evidence: `schemas/architect-evidence.schema.yaml`, `templates/architect-evidence.template.yaml`, `docs/contracts/architect-evidence.md`, `architect_evidence_schema` validator check with unit/integration tests, well-formed and malformed examples, and minimal coherence updates to the contracts READMEs, [`./BACKLOG.md`](./BACKLOG.md) §e.16, this Kanban, [`./DEPENDENCIES.md`](./DEPENDENCIES.md), [`./RISK_REGISTER.md`](./RISK_REGISTER.md), and [`../governance/CODEX_FIRST_CLASS_SCOPE.md`](../governance/CODEX_FIRST_CLASS_SCOPE.md). Architect-evidence is a separate artifact class; does not amend Batch 2D.1 review-evidence semantics and does not authorize implementer-class authoring. | Canonical-branch merge commit `51a2134 feat: add architect evidence schema contract (#36)` (PR head SHA `451be39`). |
| `post-sprint-0/cfc-2d-3-implementer-evidence-schema` | CFC follow-on Batch 2D.3 conservative machine-readable schema-class authoring slice for governed implementer evidence: `schemas/implementer-evidence.schema.yaml`, `templates/implementer-evidence.template.yaml`, `docs/contracts/implementer-evidence.md`, `implementer_evidence_schema` validator check with unit/integration tests, well-formed and malformed examples, and minimal coherence updates to the contracts READMEs, [`./BACKLOG.md`](./BACKLOG.md) §e.17, this Kanban, [`./DEPENDENCIES.md`](./DEPENDENCIES.md), [`./RISK_REGISTER.md`](./RISK_REGISTER.md), and [`../governance/CODEX_FIRST_CLASS_SCOPE.md`](../governance/CODEX_FIRST_CLASS_SCOPE.md). Implementer-evidence is a separate artifact class; does not amend Batch 2D.1 review-evidence or Batch 2D.2 architect-evidence semantics; does not authorize ratification, merge, deploy, branch deletion, branch protection mutation, live repository-settings change, provider/tool/model/host/account binding, tenant binding, or authority expansion. | Canonical-branch merge commit `01f21a5 feat: add implementer evidence schema contract (#38)` (PR head SHA `0b630be`). |
| `post-sprint-0/gate-2-lane-a-parallel-pair-rehearsal-runbook` | Gate 2 Lane A: operations rehearsal runbook for parallel pair work (`docs/operations/PARALLEL_PAIR_REHEARSAL_RUNBOOK.md`). Operational/non-normative; does not amend governance substrate, schemas, authority contracts, or identity records; public visibility remains separately gated. | Canonical-branch merge commit `a63304a docs: add parallel pair rehearsal runbook (#40)`. |
| `post-sprint-0/gate-2-lane-b-external-contributor-intake-boundary` | Gate 2 Lane B: external contributor intake boundary document (`docs/governance/EXTERNAL_CONTRIBUTOR_INTAKE_BOUNDARY.md`). `governance` / `docs` mutation class; defines intake boundary for external contributors without expanding authority, mutating schemas, identity records, or authority contracts. | Canonical-branch merge commit `8dd18a0 docs: add external contributor intake boundary (#41)`. |
| `post-sprint-0/root-worktree-lifecycle/audit` | Audit of the post-Sprint-0 operating model for substantive authoring leaking onto the root checkout, with findings condensed into [`../operations/ROOT_WORKTREE_INVARIANT.md`](../operations/ROOT_WORKTREE_INVARIANT.md) §a–§b background. | Audit findings reflected in [`../operations/ROOT_WORKTREE_INVARIANT.md`](../operations/ROOT_WORKTREE_INVARIANT.md) §a–§b and in the cross-link / template / next-task-protocol / backlog / Kanban coherence updates landing under `post-sprint-0/root-worktree-lifecycle/policy-docs-current`. |
| `post-sprint-0/root-worktree-lifecycle` | Post-Sprint-0 substrate parent for the root-worktree navigation/orchestration-only invariant and its four child gates (audit; policy/docs current; deferred checks/preflight; deferred current-root reconciliation). | Canonical-branch merge commit `30327aa docs: add root worktree invariant policy (#44)`. Parent reaches `Done` for §e.20.1 / §e.20.2; §e.20.3 (checks/preflight) and §e.20.4 (current-root reconciliation) remain `Deferred` and each require their own separately Source-ratified envelope. |
| `post-sprint-0/root-worktree-lifecycle/policy-docs-current` | Authoring of [`../operations/ROOT_WORKTREE_INVARIANT.md`](../operations/ROOT_WORKTREE_INVARIANT.md) and the minimal cross-link / template / next-task-protocol / backlog / Kanban coherence updates needed to make the root invariant canonical. `docs`-class only; no validator/preflight code, no current-root reconciliation, no GitHub-settings mutation, no public-readiness decision-record consumption. | Canonical-branch merge commit `30327aa docs: add root worktree invariant policy (#44)`. |
| `post-sprint-0/public-readiness` | Post-Sprint-0 substrate parent for the public-readiness gate and its sequenced child gates: gate-artifact authoring (`Done`) and the deferred visibility-flip envelope (`Deferred`). The parent does not mutate live GitHub settings, does not flip repository visibility, does not apply branch-protection / ruleset settings, and does not authorize CODEOWNERS, redaction-gate corpus, or any GitHub-settings mutation. | Canonical-branch merge commit `2ee63ddde7608c1bb7c9dc52dab2eadb097d2233 docs: add public readiness continuation gate (#46)`. `post-sprint-0/public-readiness/gate-artifact` (§e.21.1) is `Done`; `post-sprint-0/public-readiness/visibility-flip` (§e.21.2) remains `Deferred` and requires its own separately Source-ratified privileged envelope before the parent's deferred closure conditions are met. |
| `post-sprint-0/public-readiness/gate-artifact` | Authoring of [`./PUBLIC_READINESS_GATE.md`](./PUBLIC_READINESS_GATE.md) and minimal coherence updates to [`./README.md`](./README.md), [`./BACKLOG.md`](./BACKLOG.md), this Kanban, [`./DEPENDENCIES.md`](./DEPENDENCIES.md), [`./RISK_REGISTER.md`](./RISK_REGISTER.md), and [`../operations/ROOT_WORKTREE_INVARIANT.md`](../operations/ROOT_WORKTREE_INVARIANT.md). `docs`-class only; no validator/preflight code, no schema/template/authority/identity mutation outside the named manifest, no GitHub-settings mutation, no repository visibility flip, no CODEOWNERS authoring, no redaction-gate corpus authoring or execution. | Canonical-branch merge commit `2ee63ddde7608c1bb7c9dc52dab2eadb097d2233 docs: add public readiness continuation gate (#46)`. |

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
| `post-sprint-0/root-worktree-lifecycle/checks-preflight` | Deferred privileged `code`-class envelope authoring a `root_worktree_state` validator check, optional CLI flag(s), tests, and well-formed / malformed examples. Out of scope under the policy/docs child gate; named only so future Source ratification has a referenceable id. | `post-sprint-0/root-worktree-lifecycle` (later separately-Source-ratified privileged `code`-class envelope). |
| `post-sprint-0/root-worktree-lifecycle/current-root-reconciliation` | Deferred separately-ratified envelope to reconcile a specific operator's currently dirty root checkout back to the four root-invariant conditions, authored in an isolated per-gate worktree or clone (not on the root checkout) and without destructive remediation against unrecorded evidence per [`../operations/ROOT_WORKTREE_INVARIANT.md`](../operations/ROOT_WORKTREE_INVARIANT.md) §e. | `post-sprint-0/root-worktree-lifecycle` (later separately-Source-ratified envelope). |
| `post-sprint-0/public-readiness/visibility-flip` | Deferred separately-Source-ratified privileged envelope that would flip the canonical repository from private to public on the remote and — if Source ratifies it concurrently in the same batch — apply live branch-protection / ruleset settings to the live `main` branch. Privileged (`governance` / `security` / potentially `deploy`)-class per Feature 001 FR-008. Not authorized by the §e.21.1 gate-artifact landing per [`./PUBLIC_READINESS_GATE.md`](./PUBLIC_READINESS_GATE.md) §f and §g. | `post-sprint-0/public-readiness` (later separately-Source-ratified privileged envelope). |

### Blocked

*(No items currently in this column. `sprint-0/slice-f` has landed
on the canonical branch; see the `Done` table above.)*

## c. Immediate next likely task

CFC-1 (`post-sprint-0/cfc-1-codex-first-class`) is `Done` (PR #25
/ `30a3e8c`). CFC follow-on Batch 2A
(`post-sprint-0/cfc-2a-codex-role-decision`) is `Done` (PR #27 /
`6b51882`). CFC follow-on Batch 2B
(`post-sprint-0/cfc-2b-codex-architecture-matrix`) is `Done` (PR #28
/ `c06a3e7`). CFC follow-on Batch 2C
(`post-sprint-0/cfc-2c-codex-identity-decision`) is `Done` (PR #29
/ `66a8074`). Source ratified eight §6 decisions in
`docs/governance/CODEX_IDENTITY_RECORD_ENCODING_DECISION.md`. CFC
follow-on Codex identity record authoring
(`post-sprint-0/cfc-codex-identity-record-authoring`) is `Done`
(PR #31 / `78b57a4`); see [`./BACKLOG.md`](./BACKLOG.md) §e.14.
CFC follow-on Batch 2D.1 review-evidence schema
(`post-sprint-0/cfc-2d-1-review-evidence-schema`) is `Done`
(PR #34 / `e1f5ffc`, head `2a8fe0f`); see
[`./BACKLOG.md`](./BACKLOG.md) §e.15. CFC follow-on Batch 2D.2
architect-evidence schema
(`post-sprint-0/cfc-2d-2-architect-evidence-schema`) is `Done`
(PR #36 / `51a2134`, head `451be39`); see
[`./BACKLOG.md`](./BACKLOG.md) §e.16. CFC follow-on Batch 2D.3
implementer-evidence schema
(`post-sprint-0/cfc-2d-3-implementer-evidence-schema`) is `Done`
(PR #38 / `01f21a5`, head `0b630be`); see
[`./BACKLOG.md`](./BACKLOG.md) §e.17 and the `Done` table above.

The Codex identity record is landed on canonical main: single
Codex identity record with `role_category = architect` and
`human_ratifier_roles = ["source"]`; placeholder/unbound posture
for `allowed_repositories`, `signing_policy`, and `tenant_id`;
storage paths under `tenants/creator-engine-substrate/codex/`;
no concrete provider/tool/model/host/account binding. Batch 2D.1
review-evidence schema is also landed on canonical main as PR #34
/ `e1f5ffc` (head `2a8fe0f`): `schemas/review-evidence.schema.yaml`,
`templates/review-evidence.template.yaml`,
`docs/contracts/review-evidence.md`, the `review_evidence_schema`
validator check, and well-formed / malformed examples. Batch 2D.2
architect-evidence schema is also landed on canonical main as
PR #36 / `51a2134` (head `451be39`):
`schemas/architect-evidence.schema.yaml`,
`templates/architect-evidence.template.yaml`,
`docs/contracts/architect-evidence.md`, the
`architect_evidence_schema` validator check, and well-formed /
malformed examples; see [`./BACKLOG.md`](./BACKLOG.md) §e.16.
Batch 2D.3 implementer-evidence schema is also landed on canonical
main as PR #38 / `01f21a5` (head `0b630be`):
`schemas/implementer-evidence.schema.yaml`,
`templates/implementer-evidence.template.yaml`,
`docs/contracts/implementer-evidence.md`, the
`implementer_evidence_schema` validator check, and well-formed /
malformed examples; see [`./BACKLOG.md`](./BACKLOG.md) §e.17 and
the `Done` table above. Provider/tool/model/host/account binding
and any future unified cross-role evidence schema remain separate
downstream gates.

Gate 2 Lane A
(`post-sprint-0/gate-2-lane-a-parallel-pair-rehearsal-runbook`) is
`Done` (PR #40 / `a63304a`); see
[`./BACKLOG.md`](./BACKLOG.md) §e.18.
`docs/operations/PARALLEL_PAIR_REHEARSAL_RUNBOOK.md` is
operational/non-normative; public visibility remains separately gated.
Gate 2 Lane B
(`post-sprint-0/gate-2-lane-b-external-contributor-intake-boundary`)
is `Done` (PR #41 / `8dd18a0`); see
[`./BACKLOG.md`](./BACKLOG.md) §e.19.

The `post-sprint-0/root-worktree-lifecycle` parent and its
`post-sprint-0/root-worktree-lifecycle/policy-docs-current` child
have landed on the canonical branch as PR #44 / merge commit
`30327aa docs: add root worktree invariant policy (#44)`; both rows
are `Done` on the board above; see [`./BACKLOG.md`](./BACKLOG.md)
§e.20–§e.20.2. The sibling deferred gates
`post-sprint-0/root-worktree-lifecycle/checks-preflight` (validator
/ CLI preflight implementation) and
`post-sprint-0/root-worktree-lifecycle/current-root-reconciliation`
(reconciliation of a specific operator's dirty root) are explicitly
later gates and require their own separately-Source-ratified
envelopes; see [`./BACKLOG.md`](./BACKLOG.md) §e.20.3–§e.20.4.

The `post-sprint-0/public-readiness` parent and its
`post-sprint-0/public-readiness/gate-artifact` child have landed on
the canonical branch as PR #46 / merge commit
`2ee63ddde7608c1bb7c9dc52dab2eadb097d2233 docs: add public readiness
continuation gate (#46)`; both rows are `Done` on the board above; see
[`./BACKLOG.md`](./BACKLOG.md) §e.21–§e.21.1.
[`./PUBLIC_READINESS_GATE.md`](./PUBLIC_READINESS_GATE.md) is landed
as the canonical delivery-view public-readiness gate artifact. The
sibling `post-sprint-0/public-readiness/visibility-flip` child is
`Deferred` on the board above and is the named owning future
privileged envelope for the actual repository visibility flip (and
any concurrently-Source-ratified live branch-protection / ruleset
application). Landing the gate-artifact child does NOT authorize
making the repository public; live GitHub settings, repository
visibility, live branch-protection / ruleset application, any
CODEOWNERS decision, any future redaction-gate corpus, and any other
future GitHub-settings mutation remain separately Source-ratified and
unimplemented per
[`./PUBLIC_READINESS_GATE.md`](./PUBLIC_READINESS_GATE.md) §e–§g.
Final next-task selection — including whether the visibility-flip
envelope or any other §e residual item is in fact authorized next,
and under what bounded envelope — remains Source's.

> Downstream deferred candidates (Feature 003 extension of the landed
> `.github/` baseline; Feature 005 dispatcher / worktree automation;
> Feature 006 release / deploy execution) are each `Deferred` in
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
