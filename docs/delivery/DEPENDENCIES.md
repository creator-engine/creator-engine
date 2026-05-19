# Creator Engine Dependency Map

**Status**: Sprint 0 Slices B, C, D, E, and F are complete on the
delivery view. B1 (markdown control-plane scaffold) and B2
(Definition of Ready, Definition of Done, dependency map, risk
register) landed previously; Slice C subsequently landed on the
canonical branch as PR #12 (`1cfb955 ci: add baseline governance
validation controls`); Slice D has since landed on the
canonical branch as commit `6058661 docs: define reviewer evidence
gate for Slice D`; Slice E subsequently landed on the canonical
branch as PR #14 / commit `3cb0266 docs: add Sprint 0 Slice E
assignment runtime protocol`; and Slice F has now landed on the
canonical branch as PR #16 / commit `cb7f94a docs: add Slice F
release deploy governance policy`. Part of the **minimum repo-native
delivery control plane** and **not a Jira clone**. Markdown-only by
ratified posture. Layered on top of, and subordinate to, the
Feature 001 substrate and the Sprint 0 execution sequence. Live
GitHub branch protection settings on the remote repository remain
a separate privileged future decision and are not mutated by PR #12,
PR #14, or PR #16. The C → D edge is cleared and `sprint-0/slice-d`
is `Done` on the delivery view; the D → E edge is cleared and
`sprint-0/slice-e` is `Done` on the delivery view with durable
evidence PR #14 / `3cb0266`; the E → F edge is cleared and
`sprint-0/slice-f` is now `Done` on the delivery view with durable
evidence PR #16 / `cb7f94a`. `sprint-0/slice-f` in
[`./BACKLOG.md`](./BACKLOG.md) §c.6 is `Done` on the delivery view.
The downstream F → Feature 006 predecessor edge is therefore
cleared; Feature 006 remains `Deferred` pending its own
Source-ratified privileged envelope per §h. Post-Sprint-0 substrate
has additionally landed on the canonical branch:
`post-sprint-0/oss-readiness` (PR #20 / `35bf85f` and PR #21 /
`5b762f9`) and `post-sprint-0/workflow-hardening` (PR #22 /
`d892cd3` and PR #23 / `3dc45a1`). These post-Sprint-0 substrates
are separate from the Sprint 0 A → B → C → D → E → F dependency
chain and do not alter the Sprint 0 delivery-edge records in §g.
CFC-1 (`post-sprint-0/cfc-1-codex-first-class`) has landed on the
canonical branch as PR #25 / `30a3e8c`; it is `Done` on the delivery
view. Its predecessor edges are cleared and its successor edges
(Feature 004/CFC follow-on identity/schema work) remain separately
Source-ratified; see §d.5 and §g. CFC follow-on Batch 2A
(`post-sprint-0/cfc-2a-codex-role-decision`) has additionally landed
on the canonical branch as PR #27 / `6b51882 docs: draft Codex role
authority decision (#27)` and is `Done` on the delivery view; see
§d.6 and §g. CFC follow-on Batch 2B
(`post-sprint-0/cfc-2b-codex-architecture-matrix`) has landed on the
canonical branch as PR #28 / `c06a3e7 docs: encode Codex architecture
matrix role decision` and is `Done` on the delivery view; see §d.7
and §g. CFC follow-on Batch 2C
(`post-sprint-0/cfc-2c-codex-identity-decision`) has landed on the
canonical branch as PR #29 / `66a8074 docs: draft Codex identity
record encoding decision (#29)` and is `Done` on the delivery view;
see §d.8 and §d.9 and §g. Source ratified eight §6 decisions. The
Codex identity record authoring envelope
(`post-sprint-0/cfc-codex-identity-record-authoring`) has since
landed on the canonical branch as PR #31 / merge commit `78b57a4
docs: author Codex identity record (#31)`; see §d.9 and
[`./BACKLOG.md`](./BACKLOG.md) §e.14. CFC follow-on Batch 2D.1
review-evidence schema
(`post-sprint-0/cfc-2d-1-review-evidence-schema`) has since landed
on the canonical branch as PR #34 / merge commit `e1f5ffc feat:
add review evidence schema contract (#34)` (PR head SHA
`2a8fe0f`); see §d.10 and [`./BACKLOG.md`](./BACKLOG.md) §e.15.
CFC follow-on Batch 2D.2 architect-evidence schema
(`post-sprint-0/cfc-2d-2-architect-evidence-schema`) has since
landed on the canonical branch as PR #36 / merge commit `51a2134
feat: add architect evidence schema contract (#36)` (PR head SHA
`451be39`); see §d.11 and [`./BACKLOG.md`](./BACKLOG.md) §e.16.
CFC follow-on Batch 2D.3 implementer-evidence schema
(`post-sprint-0/cfc-2d-3-implementer-evidence-schema`) has
since landed on the canonical branch as PR #38 / merge commit
`01f21a5 feat: add implementer evidence schema contract (#38)`
(PR head SHA `0b630be`); see §d.12 and
[`./BACKLOG.md`](./BACKLOG.md) §e.17. Gate 2 Lane A
(`post-sprint-0/gate-2-parallel-pair-rehearsal`) has since landed on
the canonical branch as PR #40 / merge commit `a63304a docs: add
parallel pair rehearsal runbook (#40)`; see
[`./BACKLOG.md`](./BACKLOG.md) §e.18. Gate 2 Lane B
(`post-sprint-0/gate-2-contributor-intake-boundary`) has since landed
on the canonical branch as PR #41 / merge commit `8dd18a0 docs: add
external contributor intake boundary (#41)`; see
[`./BACKLOG.md`](./BACKLOG.md) §e.19. PR #42 / merge commit `921d46d
docs: reconcile gate 2 delivery ledgers (#42)` landed the Gate 2
delivery-ledger reconciliation; it is a reconciliation event and does
not require a new backlog row. The delivery view now reflects
canonical main at commit `921d46d8ef7e489f16158fe6b2f85f96f8bbbcec`.
The post-Sprint-0 substrate parent
`post-sprint-0/root-worktree-lifecycle` has since landed on the
canonical branch as PR #44 / merge commit `30327aa docs: add root
worktree invariant policy (#44)`; the parent row and the
`post-sprint-0/root-worktree-lifecycle/policy-docs-current` child are
now `Done`, the `post-sprint-0/root-worktree-lifecycle/audit` child
remains `Done`, and the
`post-sprint-0/root-worktree-lifecycle/checks-preflight` and
`post-sprint-0/root-worktree-lifecycle/current-root-reconciliation`
children remain `Deferred`; see [`./BACKLOG.md`](./BACKLOG.md)
§e.20. Public-readiness continuation is no longer blocked by the
policy/docs child gate; the deferred
`post-sprint-0/root-worktree-lifecycle/checks-preflight` and
`post-sprint-0/root-worktree-lifecycle/current-root-reconciliation`
gates remain later separately Source-ratified gates and are not on
the public-readiness critical path. A new post-Sprint-0 substrate
parent `post-sprint-0/public-readiness` is being authored under a
Source-ratified docs-only envelope; its
`post-sprint-0/public-readiness/gate-artifact` child is `In Progress`
and the sibling `post-sprint-0/public-readiness/visibility-flip` child
is `Deferred` as the named owning future privileged envelope for the
actual repository visibility flip; see §d.13 and
[`./BACKLOG.md`](./BACKLOG.md) §e.21. Repository visibility / live
GitHub-settings mutations remain separately Source-ratified and
unimplemented; the gate-artifact landing does not authorize the
visibility flip.

**Scope**: This document maps dependencies across Sprint 0 slices and
post-Sprint-0 features as recorded in [`./BACKLOG.md`](./BACKLOG.md).
It does not introduce new work items; it makes the dependency edges
between existing items explicit.

## a. Source-of-truth relationship

[`./BACKLOG.md`](./BACKLOG.md) is the authoritative carrier of
backlog rows and their `dependencies / blockers` fields. This
document is a **navigational map** over those edges. Where this
document and `BACKLOG.md` disagree about a dependency, `BACKLOG.md`
controls until reconciled.

Upstream sources of truth for dependency facts:

| Upstream source | Role |
|---|---|
| [`../../specs/sprint-0-minimum-viable-delivery-system/README.md`](../../specs/sprint-0-minimum-viable-delivery-system/README.md) §5 | Sprint 0 Slice A–F execution sequence and exit gates. |
| [`../product/ROADMAP.md`](../product/ROADMAP.md) §c–§g | Feature 003–006 scope summaries, deferrals, and v1.0 integration target. |
| Feature 001 substrate (`specs/001-v0-1-governance-substrate/`, `docs/contracts/`, `schemas/`, `validators/`, `examples/`, `tenants/`) | Privileged-class rule (FR-008), ratification flow (FR-016), lifecycle states (FR-013a). |
| Feature 002 spec at `specs/002-canonical-docs-and-operating-model/spec.md` | Operating-model deferrals (FR-025) and the Phase 1 / Phase 2 boundary. |
| [`./BACKLOG.md`](./BACKLOG.md) | Authoritative dependency edges on each work-item row. |
| Optional external trackers (Jira, Linear, GitHub Projects, etc.) | **Non-canonical** mirrors only. External tracker dependency claims are advisory; see §f. |

A fresh clone is sufficient to walk this map; no external tracker
credential or network state is required.

## b. Sprint 0 dependency chain

Sprint 0 slices are sequenced in alphabetical order. The chain is:

**A → B → C → D → E → F**

| Edge | Predecessor reaches | Successor becomes eligible for |
|---|---|---|
| A → B | `Done` (merged canonical-branch evidence) | `Ready` |
| B → C | `Ratified` or `Done` | `Ready`; privileged-class envelope still requires Source ratification (§e) |
| C → D | `Ratified` or `Done` | `Ready`; privileged `identity` envelope still requires Source ratification |
| D → E | `Ratified` or `Done` | `Ready`; privileged `governance` envelope still requires Source ratification |
| E → F | `Ratified` or `Done` | `Ready`; privileged `deploy` policy authoring still requires Source ratification |

Each edge satisfies the readiness criterion in
[`./DEFINITION_OF_READY.md`](./DEFINITION_OF_READY.md) §b.7. A
predecessor at `In Progress`, `Verified`, or earlier does NOT unblock
its successor.

Slice A is `Done`
([`./BACKLOG.md`](./BACKLOG.md) §c.1 cites canonical-branch commits
as durable evidence). Slice B is `Done` on the delivery view because
B1 and B2 have both landed on the canonical branch (see §c.2.1 and
§c.2.2 durable evidence on
[`./BACKLOG.md`](./BACKLOG.md)); the parent `sprint-0/slice-b` row
is decomposed in §c. The B → C edge cleared first, Slice C was
subsequently consumed under a Source-ratified privileged envelope,
and Slice C has now landed on the canonical branch as PR #12
([`./BACKLOG.md`](./BACKLOG.md) §c.3). The C → D edge cleared next,
and `sprint-0/slice-d` has since landed on the canonical branch as
commit `6058661 docs: define reviewer evidence gate for Slice D`
([`./BACKLOG.md`](./BACKLOG.md) §c.4), landing the three Slice D
delivery docs (`docs/delivery/REVIEW_GATE.md`,
`docs/delivery/REVIEW_EVIDENCE_TEMPLATE.md`,
`docs/delivery/REVIEWER_IDENTITY_REQUIREMENTS.md`) plus minimal
coherence updates. The D → E edge cleared next, and
`sprint-0/slice-e` has since landed on the canonical branch as
PR #14 / commit `3cb0266 docs: add Sprint 0 Slice E assignment
runtime protocol` ([`./BACKLOG.md`](./BACKLOG.md) §c.5), landing
the five Slice E delivery docs
(`docs/delivery/ASSIGNMENT_ENVELOPE_TEMPLATE.md`,
`docs/delivery/WORKTREE_RUNTIME_PROTOCOL.md`,
`docs/delivery/ENVELOPE_CONSUMPTION_CHECKLIST.md`,
`docs/delivery/SCOPE_AUDIT_CHECKLIST.md`,
`docs/delivery/ASSIGNMENT_ENVELOPE_DRY_RUN.md`) plus minimal
coherence updates. The E → F edge cleared next, and
`sprint-0/slice-f` has now landed on the canonical branch as PR #16
/ commit `cb7f94a docs: add Slice F release deploy governance
policy` ([`./BACKLOG.md`](./BACKLOG.md) §c.6), landing the five
Slice F delivery docs
(`docs/delivery/RELEASE_DEPLOY_GOVERNANCE.md`,
`docs/delivery/RELEASE_CANDIDATE_CHECKLIST.md`,
`docs/delivery/MERGE_APPROVAL_CHECKLIST.md`,
`docs/delivery/DEPLOYMENT_APPROVAL_POLICY.md`,
`docs/delivery/ROLLBACK_AND_POST_RELEASE_EVIDENCE.md`) plus minimal
coherence updates. The Slice F batch is policy / docs only and is
not, and never becomes, deploy automation; live deploy automation,
GitHub environments, branch protection settings, CODEOWNERS, and
Feature 006 deploy execution remain separate privileged future
decisions and are not authorized by Slice F landing per §h. The
PR #12 baseline is file-based only; live GitHub repository
settings on the remote remain a separate privileged future decision
and are not implied by the C → D edge clearing, by the Slice D
landing, by the D → E edge clearing, by the Slice E landing, by
the E → F edge clearing, or by the Slice F landing.

## c. Slice B internal dependencies

Slice B is internally decomposed into four sub-batches, only the
first two of which are in scope for Sprint 0 exit:

```
B1 (markdown control-plane scaffold) ──► B2 (DoR / DoD / dependencies / risk)
                                              │
                                              ├──► B3 (structured YAML backlog sidecars, deferred)
                                              └──► B4 (optional external-tracker mirror/adapter design, deferred)
```

### c.1 B1 → B2

- **Predecessor**: `sprint-0/slice-b/b1` — the markdown control-plane
  scaffold introduced under Slice B1
  ([`./BACKLOG.md`](./BACKLOG.md) §c.2.1).
- **Successor**: `sprint-0/slice-b/b2` — this batch
  ([`./BACKLOG.md`](./BACKLOG.md) §c.2.2).
- **Edge condition**: B1 reaches `Ratified` or `Done`.
- **Edge state**: **cleared**. B1 is `Done` on the canonical branch
  (see §c.2.1 durable evidence in
  [`./BACKLOG.md`](./BACKLOG.md)); the B1 → B2 dependency rule is
  satisfied and B2 itself has subsequently landed.
- **Why**: B2 introduces
  [`./DEFINITION_OF_READY.md`](./DEFINITION_OF_READY.md),
  [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md), this
  document, and [`./RISK_REGISTER.md`](./RISK_REGISTER.md), all of
  which are layered onto the B1 README / Backlog / Kanban /
  next-task-protocol scaffold. Authoring B2 against an unratified
  scaffold would have risked codifying contracts whose underlying
  scaffold Source had not yet accepted; B1 ratification removes
  that risk.

### c.2 B2 → B3 (deferred)

- **Predecessor**: `sprint-0/slice-b/b2`.
- **Successor**: `sprint-0/slice-b/b3` — optional structured YAML
  backlog sidecars.
- **Status**: `Deferred` per [`./BACKLOG.md`](./BACKLOG.md) §c.2.3.
- **Edge condition**: B2 reaches `Ratified` or `Done` AND Source
  ratifies a sidecar schema. Until both clear, B3 remains
  `Deferred`.
- **Why deferred**: Sprint 0 exit gate #2 is satisfied by markdown
  artifacts alone; YAML sidecars are not required.

### c.3 B2 → B4 (deferred)

- **Predecessor**: `sprint-0/slice-b/b2`.
- **Successor**: `sprint-0/slice-b/b4` — optional external-tracker
  mirror/adapter design (Jira / Linear / GitHub Projects).
- **Status**: `Deferred` per [`./BACKLOG.md`](./BACKLOG.md) §c.2.4.
- **Edge condition**: B2 reaches `Ratified` or `Done` AND Source
  ratifies an adapter design. Implementation of any adapter is a
  further separately-ratified batch.
- **Why deferred**: External trackers are non-canonical mirrors only
  ([`./README.md`](./README.md) §d). A fresh clone MUST be
  sufficient to identify the next recommended task without any
  adapter wiring.

## d. Post-Sprint-0 feature dependencies

The downstream features 003–006 each depend on a specific Sprint 0
slice's policy outline. The implementation feature instantiates the
policy that the slice authored. Feature 002 instantiated the
canonical-doc specification consumed by Slice A; no further
post-Sprint-0 work depends on Slice A independently of Slice B's
completion.

### d.1 Feature 003 depends on `sprint-0/slice-c`

- **Edge**: `sprint-0/slice-c` reaches `Ratified` or `Done` →
  `feature-003` becomes eligible for shaping.
- **Edge state**: **cleared**. Slice C is `Done`
  ([`./BACKLOG.md`](./BACKLOG.md) §c.3); Feature 003 is eligible
  for shaping but remains `Deferred` until separately Source-
  ratified.
- **Scope link**: Slice C authors the thin GitHub / CI / PR governance
  policy outline ([`./BACKLOG.md`](./BACKLOG.md) §c.3); Feature 003
  instantiates that policy as `.github/workflows/`, the PR template,
  branch protection (and live GitHub settings if Source ratifies
  that mutation), review policy / CODEOWNERS, and the CI
  verifies-not-ratifies rule
  ([`../product/ROADMAP.md`](../product/ROADMAP.md) §c). PR #12
  landed the Slice C baseline (validation workflow, PR template,
  branch protection policy file) only; the live GitHub setting and
  any extension of the baseline remain Feature-003-or-later work
  under a separately ratified privileged envelope.
- **Privileged-class note**: Feature 003 mutations are privileged
  (`governance` / `security` / `deploy`) per Feature 001 FR-008;
  ratification is required per-batch per §h.

### d.2 Feature 004 depends on `sprint-0/slice-d`

- **Edge**: `sprint-0/slice-d` reaches `Ratified` or `Done` →
  `feature-004` becomes eligible for shaping.
- **Scope link**: Slice D authors the Codex reviewer identity record
  (or equivalent), the QA / review evidence template, and the
  review-gate definition ([`./BACKLOG.md`](./BACKLOG.md) §c.4);
  Feature 004 instantiates the governed Codex / QA / security
  identities and their evidence schemas
  ([`../product/ROADMAP.md`](../product/ROADMAP.md) §d).
- **Privileged-class note**: identity creation is a privileged
  `identity`-class mutation per Feature 001 FR-008; per-identity
  ratification is required per §e.

### d.3 Feature 005 depends on `sprint-0/slice-e`

- **Edge**: `sprint-0/slice-e` reaches `Ratified` or `Done` →
  `feature-005` becomes eligible for shaping.
- **Scope link**: Slice E authors the manual Assignment Envelope
  template, worktree / branch naming conventions, the
  one-driver-per-worktree rule, envelope consumption and scope-audit
  checklists, and dry-run evidence
  ([`./BACKLOG.md`](./BACKLOG.md) §c.5); Feature 005 implements the
  Hermes dispatcher, worktree lifecycle automation, sandboxing,
  parallel runtime, and conflict-detection mapping
  ([`../product/ROADMAP.md`](../product/ROADMAP.md) §e).
- **Privileged-class note**: dispatcher policy changes are privileged
  `governance`; per-batch Source ratification is required per §e.

### d.4 Feature 006 depends on `sprint-0/slice-f`

- **Edge**: `sprint-0/slice-f` reaches `Ratified` or `Done` →
  `feature-006` becomes eligible for shaping.
- **Scope link**: Slice F authors the release-candidate checklist,
  merge-approval checklist, deployment-approval policy,
  rollback / evidence expectations, explicit `deploy` mutation
  ratification rule, and the statement of currently absent
  deployment targets / environments
  ([`./BACKLOG.md`](./BACKLOG.md) §c.6); Feature 006 instantiates
  the release agent identity, the release / deploy / rollback
  records, GitHub environments, and the Source-approved deploy gates
  for SDLC transitions T22–T24
  ([`../product/ROADMAP.md`](../product/ROADMAP.md) §f).
- **Privileged-class note**: the `deploy` mutation class is
  Source-only per Feature 001 FR-008 regardless of any Feature 006
  automation. Feature 006 implements the execution surface;
  ratification of every deploy remains Source's.

### d.5 CFC-1 depends on Sprint 0 + post-Sprint-0 substrate; precedes Feature 004/CFC follow-on

- **Item**: `post-sprint-0/cfc-1-codex-first-class`
  ([`./BACKLOG.md`](./BACKLOG.md) §e.10).
- **Predecessor edges** (all cleared):
  - Sprint 0 Slices A–F: all `Done` on the delivery view (see §b
    and §g).
  - `post-sprint-0/oss-readiness`: `Done` (PR #20 / `35bf85f` and
    PR #21 / `5b762f9`).
  - `post-sprint-0/workflow-hardening`: `Done` (PR #22 / `d892cd3`
    and PR #23 / `3dc45a1`). The workflow-hardening substrate is a
    direct prerequisite because CFC-1 Batch 1 depends on the
    pointer-only handoff, path-manifest fidelity, and transcript
    archival controls it established.
- **Why**: Batch 1 creates the governance scope and operations
  protocol that will govern any future Codex-as-actor batch.
  It is `governance/docs`-class and does not require a privileged
  predecessor beyond the completed Sprint 0 operating model and
  hardened workflow controls.
- **Landed state**: CFC-1 Batch 1 is `Done` — merged on the
  canonical branch as PR #25 / merge commit `30a3e8c docs: add CFC-1
  scope and protocol envelope`.
- **Successor edges** (not yet cleared):
  - Feature 004/CFC follow-on Batch 2+ (Codex identity record,
    review-evidence schema, architecture actor/tool matrix update):
    requires CFC-1 Batch 1 to reach `Done` AND a separate
    Source-ratified privileged envelope for each Batch 2+ item.
    These are `identity`- and `schema`-class mutations and are not
    unblocked by CFC-1 Batch 1 landing.
  - Feature 005 dispatch automation: separate predecessor chain
    (see §d.3); CFC-1 Batch 1 is not a direct predecessor of
    Feature 005.
- **Privileged-class note**: CFC-1 Batch 1 is `governance/docs`-
  class. Its successor Batch 2+ items are privileged `identity` /
  `schema` class per Feature 001 FR-008; each requires its own
  Source-ratified envelope per §h.

### d.6 CFC follow-on Batch 2A depends on CFC-1; precedes Batch 2B / 2C / 2D

- **Item**: `post-sprint-0/cfc-2a-codex-role-decision`
  ([`./BACKLOG.md`](./BACKLOG.md) §e.11).
- **Predecessor edge (cleared)**:
  `post-sprint-0/cfc-1-codex-first-class` → `post-sprint-0/cfc-2a-codex-role-decision`.
  CFC-1 is `Done` on the canonical branch (PR #25 / `30a3e8c`).
- **Why**: Batch 2A is the docs/governance decision-request gate
  that lets Source explicitly decide Codex role and authority
  semantics before any architecture actor/tool matrix update,
  Codex identity record, review/architect-evidence schema,
  validator, template, example, provider/tool/model/host/account
  binding, or authority expansion. It depends on the CFC-1 Batch 1
  scope and protocol substrate already being landed, because the
  candidate role mappings and the seven discrete Source decisions
  in Batch 2A reference the CFC-1 §3 non-authorizations and §5
  forward-scope rows.
- **Class**: `governance` / `docs`. Batch 2A did **not** mutate
  `docs/contracts/authority-matrix.yml` and did **not** amend the
  seven-row FR-015 baseline authority-matrix rule.
- **Landed state**: Batch 2A is `Done` — merged on the canonical
  branch as PR #27 / merge commit `6b51882 docs: draft Codex role
  authority decision (#27)`. Source ratified Option C (per-batch
  architect/implementer authoring assignment); Phase-1 allowed
  mutation classes = `governance`, `docs`, and `code` (with `code`
  gated to implementer-class envelopes; privileged classes
  Source-ratified); provider/tool/model/host/account binding remains
  placeholder/unbound; review evidence retained as a separate
  artifact class; `codex-architect` is a tenant/public overlay alias
  only.
- **Successor edges**:
  - Batch 2B — architecture actor/tool matrix update under
    `docs/architecture/` (`governance`-class). **Cleared and
    landed.** See §d.7.
  - Batch 2C — Codex identity record encoding decision request at
    `docs/governance/CODEX_IDENTITY_RECORD_ENCODING_DECISION.md`
    (`governance` / `docs`-class). **Cleared.** See §d.8. (Note:
    Batch 2C is itself a `governance` / `docs` decision-request
    gate that precedes the privileged `identity`-class Codex
    identity record authoring envelope; it is not the identity
    record authoring envelope itself.)
  - Batch 2D — review/architect/implementer-evidence schema
    (`schema`-class, privileged). Batch 2D.1 review-evidence
    schema has since landed (see §d.10, PR #34 / `e1f5ffc`, head
    `2a8fe0f`), Batch 2D.2 architect-evidence schema has since
    landed (see §d.11, PR #36 / `51a2134`, head `451be39`), and
    Batch 2D.3 (implementer-evidence schema) has since landed
    (see §d.12, PR #38 / `01f21a5`, head `0b630be`).

### d.7 CFC follow-on Batch 2B depends on Batch 2A; precedes Batch 2C

- **Item**: `post-sprint-0/cfc-2b-codex-architecture-matrix`
  ([`./BACKLOG.md`](./BACKLOG.md) §e.12).
- **Predecessor edge (cleared)**:
  `post-sprint-0/cfc-2a-codex-role-decision` → `post-sprint-0/cfc-2b-codex-architecture-matrix`.
  Batch 2A is `Done` (PR #27 / `6b51882`).
- **Why**: Batch 2B instantiates the Batch 2A §6.1 Option C role
  choice and the Batch 2A §6.3 authority-boundary statement in the
  architecture actor/tool matrix at
  `docs/architecture/agent-interaction-model.md` §a (Codex row) and
  §b.4 (per-batch governed authoring / review pattern). It depends
  on Batch 2A reaching `Done` because the matrix wording cites the
  Source-ratified Option C posture.
- **Class**: `governance` / `docs`. Batch 2B did **not** mutate
  `docs/contracts/identity-record.md`,
  `docs/contracts/authority-matrix.md`, `schemas/`, validators,
  templates, examples, tenants, or `.github/`.
- **Landed state**: Batch 2B is `Done` — merged on the canonical
  branch as PR #28 / merge commit `c06a3e7 docs: encode Codex
  architecture matrix role decision`. The matrix wording is now
  envelope-bound, not personality-bound; Codex retains authoring
  parity only.
- **Successor edges**:
  - Batch 2C — Codex identity record encoding decision request
    (`governance` / `docs`-class). **Cleared.** See §d.8.

### d.8 CFC follow-on Batch 2C depends on Batch 2A and Batch 2B; precedes Codex identity record authoring envelope and Batch 2D

- **Item**: `post-sprint-0/cfc-2c-codex-identity-decision`
  ([`./BACKLOG.md`](./BACKLOG.md) §e.13).
- **Predecessor edges (cleared)**:
  - `post-sprint-0/cfc-2a-codex-role-decision` → `post-sprint-0/cfc-2c-codex-identity-decision`
    (Batch 2A is `Done`; the Source-ratified Option C / Phase-1
    allowed mutation classes / placeholder-binding posture / review-
    evidence-separation posture / `codex-architect` overlay-alias
    posture are inputs to the Batch 2C encoding question).
  - `post-sprint-0/cfc-2b-codex-architecture-matrix` → `post-sprint-0/cfc-2c-codex-identity-decision`
    (Batch 2B is `Done`; the envelope-bound authority wording is
    referenced by the Batch 2C `authority_context.description` and
    `authority_context.governing_spec_refs` candidate values).
- **Why**: Batch 2C is the `governance` / `docs` decision-request
  gate that lets Source explicitly decide how the Batch 2A Option C
  semantics and the Batch 2B envelope-bound wording are encoded
  inside the existing `docs/contracts/identity-record.md` substrate
  **before** any Codex identity record authoring envelope is
  consumed. Without Batch 2C, the future identity-record authoring
  envelope would have to guess whether Codex is one record or two,
  which baseline `role_category` anchors it, and which field
  postures (`authority_context`, `human_ratifier_roles`,
  `allowed_repositories`, `signing_policy`, storage paths,
  `tenant_id`) Source ratifies.
- **Class**: `governance` / `docs`. Batch 2C does **not** mutate
  `docs/contracts/identity-record.md`,
  `docs/contracts/authority-matrix.md`,
  `schemas/identity-record.schema.yaml`,
  `docs/contracts/authority-matrix.yml`, validators, templates,
  examples, tenants, `docs/architecture/**`, or `.github/**`. The
  seven-row FR-015 baseline authority-matrix rule remains in effect
  unchanged.
- **Landed state**: Batch 2C is `Done` — merged on the canonical
  branch as PR #29 / merge commit `66a8074 docs: draft Codex identity
  record encoding decision (#29)`. Source ratified Option A (single
  record, `role_category = architect`; Option C conservative fallback
  retained); `human_ratifier_roles = ["source"]`; placeholder/unbound
  posture for `allowed_repositories`, `signing_policy`, storage
  paths, and `tenant_id`; Batch 2D reaffirmed as downstream.
- **Successor edges** (cleared for identity record authoring; Batch 2D not yet cleared):
  - **Codex identity record authoring envelope** (privileged
    `identity`-class). **Cleared.** `Done` — merged on canonical
    branch as PR #31 / merge commit `78b57a4`. See §d.9.
  - **Batch 2D — review/architect/implementer-evidence schema**
    (privileged `schema`-class). Downstream of Batch 2C and
    explicitly reaffirmed in
    [`../governance/CODEX_IDENTITY_RECORD_ENCODING_DECISION.md`](../governance/CODEX_IDENTITY_RECORD_ENCODING_DECISION.md)
    §6.8 as non-mutated by Batch 2C. Requires a separately
    Source-ratified privileged `schema`-class envelope.

### d.9 CFC follow-on Codex identity record authoring depends on Batch 2C; precedes Batch 2D

- **Item**: `post-sprint-0/cfc-codex-identity-record-authoring`
  ([`./BACKLOG.md`](./BACKLOG.md) §e.14).
- **Predecessor edge (cleared)**:
  `post-sprint-0/cfc-2c-codex-identity-decision` →
  `post-sprint-0/cfc-codex-identity-record-authoring`.
  Batch 2C is `Done` (PR #29 / `66a8074`); §6.1–§6.7 decisions
  ratified, pinning the encoding posture for the identity record.
- **Why**: The identity record authoring envelope is the privileged
  `identity`-class gate that consumes the Batch 2C §6.1–§6.7
  decisions and authors the Codex identity record under
  `tenants/creator-engine-substrate/codex/`. It requires Batch 2C
  to be `Done` because the encoding posture (`role_category =
  architect`, `human_ratifier_roles`, storage paths, `tenant_id`
  posture) is pinned by the Batch 2C ratified decisions.
- **Class**: `identity` (privileged). Does not mutate
  `docs/contracts/identity-record.md`,
  `schemas/identity-record.schema.yaml`,
  `docs/contracts/authority-matrix.md`, validators, templates,
  examples, `docs/architecture/**`, or `.github/**`. No concrete
  provider/tool/model/host/account/repository binding. Codex
  authority not expanded.
- **Landed state**: `Done` — merged on the canonical branch as
  PR #31 / merge commit `78b57a4 docs: author Codex identity record
  (#31)`. Single Codex identity record with `role_category =
  architect` and `human_ratifier_roles = ["source"]`;
  placeholder/unbound posture for `allowed_repositories`,
  `signing_policy`, and `tenant_id`; storage paths under
  `tenants/creator-engine-substrate/codex/`.
- **Successor edges** (Batch 2D.1 cleared; Batch 2D.2 cleared; Batch 2D.3 cleared):
  - **Batch 2D.1 — review-evidence schema** (privileged
    `schema`-class). **Cleared.** `Done` — merged on the canonical
    branch as PR #34 / merge commit `e1f5ffc feat: add review
    evidence schema contract (#34)` (PR head SHA `2a8fe0f`). See
    §d.10.
  - **Batch 2D.2 — architect-evidence schema** (privileged
    `schema`-class). **Cleared.** `Done` — merged on the
    canonical branch as PR #36 / merge commit `51a2134 feat: add
    architect evidence schema contract (#36)` (PR head SHA
    `451be39`). See §d.11.
  - **Batch 2D.3 — implementer-evidence schema** (privileged
    `schema`-class). **Cleared.** `Done` — merged on the canonical
    branch as PR #38 / merge commit `01f21a5 feat: add implementer
    evidence schema contract (#38)` (PR head SHA `0b630be`). See
    §d.12.

### d.10 CFC follow-on Batch 2D.1 review-evidence schema depends on Codex identity record authoring; precedes Batch 2D.2 / 2D.3

- **Item**: `post-sprint-0/cfc-2d-1-review-evidence-schema`
  ([`./BACKLOG.md`](./BACKLOG.md) §e.15).
- **Predecessor edges (cleared)**:
  `post-sprint-0/cfc-codex-identity-record-authoring` →
  `post-sprint-0/cfc-2d-1-review-evidence-schema`. Identity record
  authoring is `Done` (PR #31 / `78b57a4`). Batch 2C
  (`post-sprint-0/cfc-2c-codex-identity-decision`) and Batch 2A / 2B
  are also `Done`. The Codex-identity-record-authoring → Batch 2D.1
  predecessor edge is cleared by Batch 2D.1 landing.
- **Why**: Batch 2D.1 is the conservative `schema`-class lift of
  the existing prose review-evidence contract at
  [`./REVIEW_EVIDENCE_TEMPLATE.md`](./REVIEW_EVIDENCE_TEMPLATE.md)
  and [`../contracts/review-evidence.md`](../contracts/review-evidence.md).
  It introduces no new review process; it makes the existing
  contract machine-checkable.
- **Class**: `schema` (privileged) / `docs`. Batch 2D.1 does NOT
  mutate `docs/contracts/identity-record.md`,
  `schemas/identity-record.schema.yaml`, the authority matrix,
  mutation-class taxonomy, ratification/attestation/redaction
  contracts, `docs/architecture/**`, `docs/governance/**`,
  tenants, or `.github/**`. Architect-evidence (Batch 2D.2) and
  implementer-evidence (Batch 2D.3) schemas were not authorized by
  Batch 2D.1's envelope and required their own separately
  Source-ratified privileged `schema`-class envelopes; Batch 2D.2
  has since landed (PR #36 / `51a2134`, head `451be39`) and
  Batch 2D.3 has since landed (PR #38 / `01f21a5`, head
  `0b630be`).
- **Landed state**: `Done` — merged on the canonical branch as
  PR #34 / merge commit `e1f5ffc feat: add review evidence schema
  contract (#34)` (PR head SHA `2a8fe0f`). Landed
  `schemas/review-evidence.schema.yaml`,
  `templates/review-evidence.template.yaml`,
  `docs/contracts/review-evidence.md`, the `review_evidence_schema`
  validator check with unit and integration tests, well-formed and
  malformed examples, and minimal coherence updates to the prose
  template status pointer, the contracts README, and the Batch 2D.1
  rows in [`./BACKLOG.md`](./BACKLOG.md), [`./KANBAN.md`](./KANBAN.md),
  and this document.
- **Successor edges** (Batch 2D.2 cleared; Batch 2D.3 cleared):
  - **Batch 2D.2 — architect-evidence schema** (privileged
    `schema`-class). **Cleared.** `Done` — merged on the
    canonical branch as PR #36 / merge commit `51a2134 feat: add
    architect evidence schema contract (#36)` (PR head SHA
    `451be39`). See §d.11.
  - **Batch 2D.3 — implementer-evidence schema** (privileged
    `schema`-class). **Cleared.** `Done` — merged on the canonical
    branch as PR #38 / merge commit `01f21a5 feat: add implementer
    evidence schema contract (#38)` (PR head SHA `0b630be`). See
    §d.12.

### d.11 CFC follow-on Batch 2D.2 architect-evidence schema depends on Batch 2D.1; precedes Batch 2D.3

- **Item**: `post-sprint-0/cfc-2d-2-architect-evidence-schema`
  ([`./BACKLOG.md`](./BACKLOG.md) §e.16).
- **Predecessor edges (cleared)**:
  `post-sprint-0/cfc-2d-1-review-evidence-schema` →
  `post-sprint-0/cfc-2d-2-architect-evidence-schema`. Batch 2D.1
  is `Done` (PR #34 / `e1f5ffc`, head `2a8fe0f`). Prior CFC
  follow-on Batches 2A / 2B / 2C and the Codex identity record
  authoring envelope are also `Done`.
- **Why**: Batch 2D.2 is the conservative `schema`-class authoring
  slice for governed architect evidence. It is a sibling artifact
  class to Batch 2D.1 review-evidence; it preserves the Batch 2A
  §6.3 ratified authority-boundary posture (architect parity is
  authoring parity, not ratification/merge/deploy authority) and
  the Batch 2B envelope-bound authority wording. It does not amend
  the Batch 2D.1 review-evidence schema/template/contract/validator
  /examples and does not authorize implementer-class authoring.
- **Class**: `schema` (privileged) / `docs`. Batch 2D.2 does NOT
  mutate `docs/contracts/identity-record.md`,
  `schemas/identity-record.schema.yaml`, the authority matrix,
  mutation-class taxonomy, ratification/attestation/redaction
  contracts, `docs/architecture/**`,
  `docs/governance/CODEX_IDENTITY_RECORD_ENCODING_DECISION.md`,
  `docs/governance/CODEX_ROLE_AND_AUTHORITY_DECISION.md`,
  tenants, `.github/**`, or any Batch 2D.1 review-evidence
  artifact. Batch 2D.3 (implementer-evidence schema) remains
  downstream and is not authored under this envelope.
- **Landed state**: `Done` — merged on the canonical branch as
  PR #36 / merge commit `51a2134 feat: add architect evidence
  schema contract (#36)` (PR head SHA `451be39`). Landed
  `schemas/architect-evidence.schema.yaml`,
  `templates/architect-evidence.template.yaml`,
  `docs/contracts/architect-evidence.md`, the
  `architect_evidence_schema` validator check with unit and
  integration tests, well-formed and malformed examples, and
  minimal coherence updates to the contracts READMEs, the
  Batch 2D.2 rows in [`./BACKLOG.md`](./BACKLOG.md),
  [`./KANBAN.md`](./KANBAN.md), this document, and
  [`./RISK_REGISTER.md`](./RISK_REGISTER.md), and
  [`../governance/CODEX_FIRST_CLASS_SCOPE.md`](../governance/CODEX_FIRST_CLASS_SCOPE.md).
- **Successor edges** (Batch 2D.3 cleared):
  - **Batch 2D.3 — implementer-evidence schema** (privileged
    `schema`-class). **Cleared.** `Done` — merged on the canonical
    branch as PR #38 / merge commit `01f21a5 feat: add implementer
    evidence schema contract (#38)` (PR head SHA `0b630be`). See
    §d.12.

### d.12 CFC follow-on Batch 2D.3 implementer-evidence schema depends on Batch 2D.2

- **Item**: `post-sprint-0/cfc-2d-3-implementer-evidence-schema`
  ([`./BACKLOG.md`](./BACKLOG.md) §e.17).
- **Predecessor edges (cleared)**:
  `post-sprint-0/cfc-2d-2-architect-evidence-schema` →
  `post-sprint-0/cfc-2d-3-implementer-evidence-schema`. Batch 2D.2
  is `Done` (PR #36 / `51a2134`, head `451be39`). Prior CFC
  follow-on Batches 2A / 2B / 2C / 2D.1 and the Codex identity
  record authoring envelope are also `Done`.
- **Why**: Batch 2D.3 is the conservative `schema`-class authoring
  slice for governed implementer evidence. It is a sibling
  artifact class to Batch 2D.1 review-evidence and Batch 2D.2
  architect-evidence; it preserves the Batch 2A §6.3 ratified
  authority-boundary posture (architect/implementer parity is
  authoring/execution parity, not ratification/merge/deploy
  authority) and the Batch 2B envelope-bound authority wording.
  It does not amend the Batch 2D.1 review-evidence or Batch 2D.2
  architect-evidence schema/template/contract/validator/examples
  and does not authorize ratification, merge, deploy, branch
  deletion, branch protection mutation, live repository-settings
  change, provider/tool/model/host/account binding, tenant
  binding, or authority expansion.
- **Class**: `schema` (privileged) / `docs`. Batch 2D.3 does NOT
  mutate `docs/contracts/identity-record.md`,
  `schemas/identity-record.schema.yaml`, the authority matrix,
  mutation-class taxonomy, ratification/attestation/redaction
  contracts, `docs/architecture/**`,
  `docs/governance/CODEX_IDENTITY_RECORD_ENCODING_DECISION.md`,
  `docs/governance/CODEX_ROLE_AND_AUTHORITY_DECISION.md`,
  tenants, `.github/**`, or any Batch 2D.1 review-evidence or
  Batch 2D.2 architect-evidence artifact.
- **Landed state**: `Done` — merged on the canonical branch as
  PR #38 / merge commit `01f21a5 feat: add implementer evidence
  schema contract (#38)` (PR head SHA `0b630be`). Landed
  `schemas/implementer-evidence.schema.yaml`,
  `templates/implementer-evidence.template.yaml`,
  `docs/contracts/implementer-evidence.md`, the
  `implementer_evidence_schema` validator check with unit and
  integration tests, well-formed and malformed examples, and
  minimal coherence updates to the contracts READMEs, the
  Batch 2D.3 rows in [`./BACKLOG.md`](./BACKLOG.md),
  [`./KANBAN.md`](./KANBAN.md), this document,
  [`./RISK_REGISTER.md`](./RISK_REGISTER.md), and
  [`../governance/CODEX_FIRST_CLASS_SCOPE.md`](../governance/CODEX_FIRST_CLASS_SCOPE.md).
- **Successor edges**: Any future unified cross-role evidence
  schema or downstream evidence consumer remains explicitly
  downstream and requires its own separately Source-ratified
  privileged `schema`-class envelope.

### d.13 Public-readiness gate depends on root-worktree policy/docs landing; precedes visibility-flip envelope

- **Items**: `post-sprint-0/public-readiness` parent
  ([`./BACKLOG.md`](./BACKLOG.md) §e.21);
  `post-sprint-0/public-readiness/gate-artifact` child
  ([`./BACKLOG.md`](./BACKLOG.md) §e.21.1);
  `post-sprint-0/public-readiness/visibility-flip` deferred child
  ([`./BACKLOG.md`](./BACKLOG.md) §e.21.2).
- **Predecessor edges (cleared)** for the gate-artifact child:
  `post-sprint-0/oss-readiness` (`Done`, PR #20 / `35bf85f` and
  PR #21 / `5b762f9`);
  `post-sprint-0/workflow-hardening` (`Done`, PR #22 / `d892cd3`
  and PR #23 / `3dc45a1`);
  `post-sprint-0/root-worktree-lifecycle/policy-docs-current`
  (`Done`, PR #44 / `30327aa`).
- **Why**: The gate-artifact child authors
  [`./PUBLIC_READINESS_GATE.md`](./PUBLIC_READINESS_GATE.md) and the
  minimal coherence updates required to discover it. It depends on
  the root-worktree policy/docs landing because the gate artifact's
  named owning future privileged envelope for the visibility flip
  (§e.21.2) must observe
  [`../operations/ROOT_WORKTREE_INVARIANT.md`](../operations/ROOT_WORKTREE_INVARIANT.md)
  as one of its upstream constraints. It depends on the open-source
  readiness substrate (PR #20 / `35bf85f` and PR #21 / `5b762f9`)
  because the gate artifact cites that substrate as the already-
  landed public-readiness substrate. It depends on the workflow-
  hardening protocol set (PR #22 / `d892cd3`, PR #23 / `3dc45a1`,
  PR #44 / `30327aa`) because the visibility-flip envelope must
  observe the controller-seat-boundary, pointer-only-relay,
  path-manifest-fidelity, transcript-archive, and root-worktree-
  invariant controls.
- **Class**: `docs` for the gate-artifact child; `governance` /
  `security` (privileged), potentially `deploy` if live branch-
  protection / ruleset settings are ratified in the same batch, for
  the deferred visibility-flip child.
- **Landed / in-flight state**: gate-artifact child is `In Progress`
  under a Source-ratified docs-only authoring envelope; deferred
  visibility-flip child remains `Deferred` and requires its own
  separately Source-ratified privileged envelope.
- **Successor edges (deferred)** for the gate-artifact child:
  `post-sprint-0/public-readiness/visibility-flip` — privileged
  visibility-flip envelope. Cleared as a predecessor edge by the
  gate-artifact reaching `Done`, but the visibility-flip envelope
  itself remains `Deferred` and is not authorized to consume until
  Source ratifies a privileged envelope for it per §h. Other §e
  residual items in
  [`./PUBLIC_READINESS_GATE.md`](./PUBLIC_READINESS_GATE.md) §e
  (live branch-protection / ruleset application; any CODEOWNERS
  decision; any future redaction-gate corpus; any other future
  GitHub-settings mutation) MAY be ratified under separate envelopes
  from the visibility flip and are not on the gate artifact's
  critical path.

## e. v1.0 integration target

v1.0 is an integration target reached when Features 001 through 006
have landed and Sprint 0 exit gates 1–12 are satisfied
([`../product/ROADMAP.md`](../product/ROADMAP.md) §g). Its
dependency closure is:

| Dependency | Required state |
|---|---|
| `sprint-0/slice-a` | `Done` |
| `sprint-0/slice-b` (B1 and B2) | `Done` |
| `sprint-0/slice-c` | `Done` |
| `sprint-0/slice-d` | `Done` |
| `sprint-0/slice-e` | `Done` |
| `sprint-0/slice-f` | `Done` |
| `feature-003` | `Done` (implements Slice C policy outline) |
| `feature-004` | `Done` (instantiates Slice D identities and schemas) |
| `feature-005` | `Done` (implements Slice E manual protocol as automation) |
| `feature-006` | `Done` (implements Slice F policy as release / deploy execution) |

v1.0 is not a feature in itself; it is the named state at which the
full SDLC state machine is exercised end-to-end with every privileged
gate human-ratified. The Phase 1 / Phase 2 boundary in Feature 002
applies: Phase 2 expansion is itself a ratified amendment and is not
implemented by v1.0.

## f. Reserved item — US3 A1

- **Item**: `us3/a1` ([`./BACKLOG.md`](./BACKLOG.md) §d).
- **Current status**: `Blocked` / `Deferred`.
- **Blockers**:
  1. Sprint 0 MUST reach exit (every Sprint 0 exit gate satisfied,
     including those that v1.0 depends on under §e).
  2. Source MUST explicitly ratify a future spec authorizing the US3
     A1 area before any implementation begins.
- **Why**: US3 A1 is recorded only as a referenceable id; its
  mutation class is to be determined by the future spec and MUST be
  treated as potentially privileged until classified. Starting work
  on US3 A1 before both blockers clear is an authority conflict per
  Feature 002 FR-018 and a contract violation of the Sprint 0
  execution sequence in
  [`../../specs/sprint-0-minimum-viable-delivery-system/README.md`](../../specs/sprint-0-minimum-viable-delivery-system/README.md)
  §5.

## g. Dependency status table

This table summarizes the current state of each dependency edge
using the eight-column delivery-view status vocabulary from
[`./BACKLOG.md`](./BACKLOG.md) §a. It is a derivative view; rows
that change in `BACKLOG.md` MUST be re-derived here under the
post-merge update procedure in
[`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §d.

| Predecessor | Successor | Predecessor delivery status | Edge state |
|---|---|---|---|
| `sprint-0/slice-a` | `sprint-0/slice-b` | `Done` | Cleared. |
| `sprint-0/slice-b/b1` | `sprint-0/slice-b/b2` | `Done` | Cleared; B1 landed on the canonical branch. |
| `sprint-0/slice-b/b2` | `sprint-0/slice-b/b3` | `Done` | B1 → B2 → B3 predecessor rule cleared by B2 landing; successor remains `Deferred` pending a Source-ratified sidecar schema. |
| `sprint-0/slice-b/b2` | `sprint-0/slice-b/b4` | `Done` | B1 → B2 → B4 predecessor rule cleared by B2 landing; successor remains `Deferred` pending a Source-ratified adapter design. |
| `sprint-0/slice-b` | `sprint-0/slice-c` | `Done` | Cleared; Slice B is complete on the delivery view. Successor `Done` as of PR #12 (`1cfb955`). |
| `sprint-0/slice-c` | `sprint-0/slice-d` | `Done` | Cleared; both predecessor and successor have landed on the canonical branch (Slice D durable evidence: commit `6058661 docs: define reviewer evidence gate for Slice D`). |
| `sprint-0/slice-d` | `sprint-0/slice-e` | `Done` | Cleared; both predecessor and successor have landed on the canonical branch (Slice E durable evidence: PR #14 / commit `3cb0266 docs: add Sprint 0 Slice E assignment runtime protocol`). |
| `sprint-0/slice-e` | `sprint-0/slice-f` | `Done` | Cleared; both predecessor and successor have landed on the canonical branch (Slice F durable evidence: PR #16 / commit `cb7f94a docs: add Slice F release deploy governance policy`). |
| `sprint-0/slice-c` | `feature-003` | `Done` | Predecessor `Done`; successor remains `Deferred`. Live GitHub branch protection settings and any extension of the landed `.github/` baseline (CODEOWNERS, etc.) still require a separately ratified privileged envelope per §h. |
| `sprint-0/slice-d` | `feature-004` | `Done` | Predecessor `Done`; successor remains `Deferred`. Privileged `identity` envelope for Feature 004 still requires §e. |
| `sprint-0/slice-e` | `feature-005` | `Done` | Predecessor `Done`; successor remains `Deferred`. Privileged `governance` envelope still requires §e. |
| `sprint-0/slice-f` | `feature-006` | `Done` | Predecessor `Done` (PR #16 / `cb7f94a`); successor remains `Deferred`. Privileged `deploy` envelope for Feature 006 release / deploy execution still requires §e; the Slice F batch is policy / docs only and does not authorize Feature 006 implementation. |
| Sprint 0 exit (gates 1–12) + Features 003–006 | `v1.0` | mixed (`Done` / `Deferred` / `Blocked`) | Successor `Deferred` until every dependency in §e is `Done`. |
| Sprint 0 exit + Source-ratified future spec | `us3/a1` | (not yet specced) | Successor `Blocked` / `Deferred` per §f. |
| Sprint 0 (all slices) + `post-sprint-0/oss-readiness` + `post-sprint-0/workflow-hardening` | `post-sprint-0/cfc-1-codex-first-class` | `Done` (all predecessors) | Predecessor edges cleared; CFC-1 is `Done` — landed on canonical branch as PR #25 / `30a3e8c`. See §d.5. |
| `post-sprint-0/cfc-1-codex-first-class` | Feature 004/CFC follow-on Batch 2+ (identity record authoring `Done`; Batch 2D.1 review-evidence schema `Done`; Batch 2D.2 architect-evidence schema `Done`; Batch 2D.3 implementer-evidence schema `Done`; architecture update and other downstream envelopes not yet shaped) | `Done` (CFC-1; identity record authoring; Batch 2D.1; Batch 2D.2; Batch 2D.3) | CFC-1 is `Done` (PR #25 / `30a3e8c`); Codex identity record authoring is `Done` (PR #31 / `78b57a4`); Batch 2D.1 review-evidence schema is `Done` (PR #34 / `e1f5ffc`, head `2a8fe0f`); Batch 2D.2 architect-evidence schema is `Done` (PR #36 / `51a2134`, head `451be39`); Batch 2D.3 implementer-evidence schema is `Done` (PR #38 / `01f21a5`, head `0b630be`). Other downstream envelopes (architecture update, future unified cross-role evidence schema or downstream evidence consumer, provider/tool/model/host/account binding, tenant binding, deploy/dispatch, and any authority expansion) remain not yet shaped and require separate Source-ratified privileged envelopes per §h. Not authorized by CFC-1 Batch 1 landing. |
| `post-sprint-0/cfc-1-codex-first-class` | `post-sprint-0/cfc-2a-codex-role-decision` | `Done` (CFC-1) | Cleared; CFC-1 is `Done` (PR #25 / `30a3e8c`); successor is `Done` (PR #27 / `6b51882`). `governance` / `docs` class; non-privileged predecessor edge. See §d.6. |
| `post-sprint-0/cfc-2a-codex-role-decision` | `post-sprint-0/cfc-2b-codex-architecture-matrix` | `Done` (Batch 2A) | Cleared; predecessor is `Done` (PR #27 / `6b51882`); successor is `Done` (PR #28 / `c06a3e7`). `governance` / `docs` class. See §d.7. |
| `post-sprint-0/cfc-2a-codex-role-decision` + `post-sprint-0/cfc-2b-codex-architecture-matrix` | `post-sprint-0/cfc-2c-codex-identity-decision` | `Done` (both predecessors) | Cleared; both predecessors are `Done`; successor is `Done` — merged on the canonical branch as PR #29 / `66a8074`. Source ratified eight §6 decisions. `governance` / `docs` class; non-privileged predecessor edges. See §d.8. |
| `post-sprint-0/cfc-2c-codex-identity-decision` | `post-sprint-0/cfc-codex-identity-record-authoring` (Codex identity record authoring, `identity`-class, privileged) | `Done` (Batch 2C and identity record authoring) | Batch 2C is `Done` (PR #29 / `66a8074`); §6.1–§6.7 decisions ratified. Successor identity record authoring is `Done` — merged on canonical branch as PR #31 / merge commit `78b57a4`; single Codex identity record with `role_category = architect`, `human_ratifier_roles = ["source"]`, placeholder/unbound posture; storage paths under `tenants/creator-engine-substrate/codex/`. See §d.9. |
| `post-sprint-0/cfc-codex-identity-record-authoring` | `post-sprint-0/cfc-2d-1-review-evidence-schema` (Batch 2D.1 review-evidence schema lift, `schema`-class, privileged) | `Done` (identity record authoring; Batch 2D.1) | Identity record authoring is `Done` (PR #31 / `78b57a4`). Batch 2D.1 successor is `Done` — merged on the canonical branch as PR #34 / `e1f5ffc` (PR head SHA `2a8fe0f`). See §d.10. |
| `post-sprint-0/cfc-2d-1-review-evidence-schema` | `post-sprint-0/cfc-2d-2-architect-evidence-schema` (Batch 2D.2 architect-evidence schema, `schema`-class, privileged) | `Done` (Batch 2D.1) | Cleared; Batch 2D.1 is `Done` (PR #34 / `e1f5ffc`, head `2a8fe0f`); successor Batch 2D.2 is `Done` — merged on the canonical branch as PR #36 / `51a2134` (PR head SHA `451be39`); Batch 2D.3 (implementer-evidence schema) has since landed (PR #38 / `01f21a5`, head `0b630be`). See §d.10, §d.11, and §d.12. |
| `post-sprint-0/cfc-2d-2-architect-evidence-schema` | `post-sprint-0/cfc-2d-3-implementer-evidence-schema` (Batch 2D.3 implementer-evidence schema, `schema`-class, privileged) | `Done` (Batch 2D.2) | Predecessor is `Done` (PR #36 / `51a2134`, head `451be39`); successor Batch 2D.3 is `Done` — merged on the canonical branch as PR #38 / `01f21a5` (PR head SHA `0b630be`). See §d.11 and §d.12. |
| `post-sprint-0/cfc-2c-codex-identity-decision` | CFC follow-on Batch 2D (review/architect/implementer-evidence schema, `schema`-class, privileged) | `Done` (Batch 2C) | Batch 2C is `Done` (PR #29 / `66a8074`); Batch 2D explicitly reaffirmed as non-mutated by Batch 2C per [`../governance/CODEX_IDENTITY_RECORD_ENCODING_DECISION.md`](../governance/CODEX_IDENTITY_RECORD_ENCODING_DECISION.md) §6.8. Batch 2D.1 review-evidence schema has since landed (PR #34 / `e1f5ffc`, head `2a8fe0f`), Batch 2D.2 architect-evidence schema has since landed (PR #36 / `51a2134`, head `451be39`), and Batch 2D.3 (implementer-evidence) has since landed (PR #38 / `01f21a5`, head `0b630be`). Any future unified cross-role evidence schema or downstream evidence consumer remains downstream and requires its own separately Source-ratified privileged envelope per §h. |
| `post-sprint-0/oss-readiness` + `post-sprint-0/workflow-hardening` + `post-sprint-0/root-worktree-lifecycle/policy-docs-current` | `post-sprint-0/public-readiness/gate-artifact` (`docs`-class) | `Done` (all predecessors) | Cleared; predecessors are `Done` (PR #20 / `35bf85f`, PR #21 / `5b762f9`, PR #22 / `d892cd3`, PR #23 / `3dc45a1`, PR #44 / `30327aa`). Gate-artifact successor is `In Progress` under a Source-ratified docs-only authoring envelope, landing [`./PUBLIC_READINESS_GATE.md`](./PUBLIC_READINESS_GATE.md) and the minimal coherence updates. See §d.13. |
| `post-sprint-0/public-readiness/gate-artifact` | `post-sprint-0/public-readiness/visibility-flip` (privileged `governance` / `security` / potentially `deploy`-class) | `In Progress` (gate-artifact) | Predecessor `In Progress`; successor remains `Deferred`. The visibility-flip envelope is the named owning future privileged envelope for the actual repository visibility flip and any concurrently-Source-ratified live branch-protection / ruleset application; it is not authorized by the gate-artifact landing per [`./PUBLIC_READINESS_GATE.md`](./PUBLIC_READINESS_GATE.md) §f and §g and still requires §h. See §d.13. |

## h. Rule — privileged dependencies require ratification requests, not implementation shortcuts

A dependency is **privileged** when clearing it requires a mutation
in any of `deploy`, `governance`, `identity`, `security`,
`attestation`, or `redaction` per Feature 001 FR-008.

When the action required to clear a privileged dependency is itself
a privileged mutation, the next task is a **ratification request to
Source**, not the implementation. This rule mirrors
[`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §c.5 and is
restated here for the dependency map:

1. The implementer MUST NOT begin work on the privileged dependency
   simply because the upstream edge has cleared. The envelope must
   itself be Source-ratified before consumption (Feature 002 FR-008).
2. A passing CI run, agent review text, an external tracker green
   check, or a "go ahead" message on a non-designated surface MUST
   NOT substitute for Source ratification of the privileged envelope.
3. Author/approver separation (Feature 001 FR-007) applies: the
   actor who will author the privileged mutation MUST NOT be its
   ratifier.
4. The fastest path to unblock a downstream item that depends on a
   privileged predecessor is to land the predecessor under a
   Source-ratified envelope — not to shortcut the predecessor's
   readiness or done gate.

Examples in this map: every Slice C–F edge, every Feature 003–006
edge, and every privileged-class branch of v1.0 fall under this rule.

## i. Rule — external tracker dependencies are advisory unless mirrored in the repo-visible backlog

External tracker entries (Jira, Linear, GitHub Projects, or any
future adapter ratified under Slice B4) are **non-canonical** per
[`./README.md`](./README.md) §d. For the dependency map:

1. An external tracker entry MAY appear as an `external_tracker_ref`
   on a backlog row, but it is a non-canonical pointer. It does NOT
   introduce a dependency edge into this map.
2. A dependency claim that exists only in an external tracker is
   **advisory**. It MUST NOT block, unblock, or otherwise change the
   status of a repo-visible backlog item until the claim is mirrored
   into [`./BACKLOG.md`](./BACKLOG.md) and Source ratifies the
   updated row.
3. If an external tracker entry and the repo-visible backlog
   disagree about a dependency edge, the repo-visible backlog
   controls until Source ratifies an update. The disagreement is
   recorded per
   [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §c.6 and
   resolves into either a backlog amendment or a tracker correction.
4. A fresh clone with no network access and no tracker credential
   MUST be sufficient to walk this map. Dependency edges that are
   only visible via an external tracker are not part of the map.

## j. Maintenance rules

1. New dependency edges are introduced by adding or amending the
   `dependencies / blockers` field on the relevant backlog row in
   [`./BACKLOG.md`](./BACKLOG.md). This document is then re-derived
   from that row under the post-merge update procedure in
   [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §d.
2. The Sprint 0 chain **A → B → C → D → E → F** is a structural
   invariant of Sprint 0 execution
   ([`../../specs/sprint-0-minimum-viable-delivery-system/README.md`](../../specs/sprint-0-minimum-viable-delivery-system/README.md)
   §5). Any proposal to reorder the chain is a privileged
   `governance` amendment per §h.
3. The privileged-class note on each edge MUST NOT be silently
   dropped. A privileged envelope that lands without Source
   ratification recorded against it is a contract violation per
   Feature 002 FR-008 and an authority conflict per FR-018.
4. Instance-local facts (absolute filesystem paths, in-flight PR
   numbers, terminal pane identifiers, local session queues,
   secrets, credentials, tokens) MUST NOT enter this document. Only
   merged PR numbers in canonical-branch commit subjects MAY be
   cited as historical evidence.

## k. Acceptance posture for B2

This document satisfies the B2 envelope's dependency-map
requirements:

- Names the Sprint 0 dependency chain **A → B → C → D → E → F**
  (§b).
- Names the B1 → B2 edge inside Slice B and the B3 / B4 deferred
  successors of B2 (§c).
- Names the Feature 003 → Slice C, Feature 004 → Slice D, Feature
  005 → Slice E, and Feature 006 → Slice F edges (§d).
- Names the v1.0 dependency closure on Sprint 0 exit and Features
  003–006 (§e).
- Names the reserved US3 A1 item as `Blocked` until Sprint 0 exits
  and Source ratifies a future spec (§f).
- Provides a dependency status table using the eight delivery-view
  statuses (§g).
- States the rule that privileged dependencies require ratification
  requests, not implementation shortcuts (§h).
- States the rule that external tracker dependencies are advisory
  unless mirrored in the repo-visible backlog (§i).
