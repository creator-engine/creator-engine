# Creator Engine Roadmap

**Status**: Canonical. Authored under Sprint 0 Execution Slice A.

**Source-of-truth relationship**: SUMMARY. ROADMAP.md summarizes
Feature 001's scope (authoritative under
[`specs/001-v0-1-governance-substrate/`](../../specs/001-v0-1-governance-substrate/)
and [`docs/contracts/`](../contracts/)) and forward-references the
Feature 003 through Feature 006 scopes; it never redefines them. The
canonical sequencing source for Features 001 and 002 already exists in
the merged repository; the future-feature entries here are scope
summaries with named deferrals, not implementation promises.

Sprint 0 Execution sequencing — and the Sprint 0 exit gates — live in
[`../../specs/sprint-0-minimum-viable-delivery-system/README.md`](../../specs/sprint-0-minimum-viable-delivery-system/README.md).
Slice A (this batch) advances only the canonical-docs gate. Sprint 0
is not complete merely because the canonical documents exist.

## a. Feature 001 — v0.1 governance substrate (scope summary)

**Status**: Merged.

**Source-of-truth**: `specs/001-v0-1-governance-substrate/spec.md`,
`docs/contracts/`, `schemas/`, `validators/`, `examples/`,
`tenants/<tenant>/`.

Feature 001 ships the law: the contracts a Creator-Engine-governed
mutation must satisfy and the offline validator that checks them.

- Tenant identity record schema (FR-001) and platform/tenant identity
  distinction (FR-002), with GitHub App installation as the v0.1
  source-host reference (FR-003).
- Attestation record format binding a mutation to spec, identity,
  mutation class, permitted actions, verification evidence, and
  ratifier (FR-004), reconstructable from repository artifacts alone
  (FR-005).
- Mutation-class taxonomy with nine baseline classes (`docs`, `code`,
  `schema`, `deploy`, `governance`, `identity`, `security`,
  `attestation`, `redaction`), reserved-action vocabulary, and tenant
  extension overlay rules (FR-006).
- Author/approver separation rule (FR-007).
- Privileged-class ratification rule (FR-008): `deploy`, `governance`,
  `identity`, `security`, `attestation`, and `redaction` require
  explicit human ratification.
- Spec wrapper schema (`spec.creator-engine.yml`) and plan/tasks
  sidecars (FR-009, FR-012a, FR-012b); Spec Kit files remain
  byte-identical (FR-010).
- Definition of Ready (FR-013), spec status lifecycle in six states
  `draft → ready → in_progress → verified → ratified → done`
  (FR-013a), and Definition of Done (FR-014).
- Authority matrix (FR-015) with seven baseline role categories
  (`source`, `ratifier`, `reviewer`, `architect`, `implementer`,
  `verifier`, `observer`); ratification flow (FR-016).
- Redaction gate policy and records (FR-019, FR-020, FR-020a, FR-021).
- Dogfood tenant fixture under `tenants/<tenant>/` with zero
  unresolved fields (FR-022, FR-023), and the no-tenant-identifier
  rule for generic-contract paths (FR-024).
- Offline validator (FR-025–FR-027a) runnable from a fresh `git clone`.
- Example tenant files (FR-028, FR-029) and verification specification
  (FR-030, FR-031).

**Deferral rationale**: Feature 001 ships substrate contracts only. It
does not ship the canonical operating-model documents (that is Feature
002), `.github/` automation (Feature 003), governed reviewer/QA/security
identities (Feature 004), dispatcher/runtime (Feature 005), or release
automation (Feature 006). The substrate is the precondition for those
later features.

## b. Feature 002 — v0.1-docs operating model (scope summary)

**Status**: Merged as a specification. Canonical document bodies authored
under Sprint 0 Execution Slice A (this batch).

**Source-of-truth**:
`specs/002-canonical-docs-and-operating-model/spec.md`.

Feature 002 ships the civilization: the operating model future
automation must obey.

- SDLC state machine of exactly 25 states from `Idea/Intent` to
  `Post-release Evidence Recorded` (FR-001) and the 24-transition
  matrix with responsible actor/tool, authorizing gate, Phase 1 / Phase
  2-eligible label, and required evidence (FR-002, FR-003).
- Mapping to Feature 001's six-state spec lifecycle (FR-004); Feature
  002 defers to Feature 001 where they overlap.
- Assignment Envelope spec (FR-005) with author/approver separation
  (FR-006), single-use semantics (FR-007), and Source ratification for
  envelopes touching privileged classes (FR-008).
- `/speckit-implement` policy (FR-009, FR-010, FR-011): mandatory
  inside an envelope, prohibited outside; Hermes authors, Claude
  consumes, Source ratifies privileged integration.
- Actor/tool ownership matrix (FR-012, FR-013, FR-014) for Source,
  Nefarious/Hermes, Claude Code, Codex, QA agent, security agent,
  release agent, CI, and GitHub — with presence categories
  (operationally active; named with identity record deferred; named
  with automation deferred).
- Parallel-agent development model (FR-015, FR-016): one driver per
  physical worktree; many isolated writers via separate
  branches/worktrees/envelopes; canonical-branch integration
  serialized and Source-ratified. The temporary May 10 freeze is NOT
  the permanent model.
- Conflict taxonomy (FR-017, FR-018) with exactly four classes:
  `textual`, `file/task ownership`, `semantic`, `authority`. The
  `authority` class hard-stops work and requires Source ratification.
- Source-of-truth hierarchy (FR-019–FR-021): constitution > Feature
  001 substrate (ratified) > Feature 002 canonical docs > tenant
  fixtures > working notes and handoffs.
- Canonical document set (FR-022) of exactly 17 documents, with
  per-document purpose, required sections, source-of-truth
  relationship, and acceptance criteria (FR-023); document bodies are
  authored after Feature 002 ratification (FR-024).
- Automation deferrals (FR-025) naming Features 003 through 006 as
  owners.
- Phase 1 / Phase 2 boundary (FR-027, FR-028): Feature 002 defines the
  boundary; Phase 2 is not implemented and any Phase 2 expansion is a
  ratified amendment.
- Operating-model governance (FR-029, FR-030).

**Deferral rationale**: Feature 002 is specification-only at the
operating-model layer. Authoring the canonical document bodies (this
batch) advances the documentation gate but does not implement
`.github/`, governed reviewer/QA identities, dispatcher runtime, or
release/deploy automation.

## c. Feature 003 — GitHub CI governance (scope summary)

**Status**: Deferred. Not yet specced.

Feature 003 will own the `.github/` content Feature 002 specifies but
does not author:

- `.github/workflows/` baseline validation workflow (tests, lint,
  typecheck, build, Creator Engine validator, schema validation).
- PR template surfacing scope, validation evidence, review evidence,
  mutation classes, deferrals, and Source ratification requirements.
- Branch protection policy (and live GitHub settings if Source
  ratifies that mutation) requiring CI evidence before merge.
- Review policy / CODEOWNERS policy as applicable.
- CI mutation-class ratification rule: CI policy or workflow changes
  are themselves a privileged `governance`/`security`/`deploy` mutation
  per Feature 001 FR-008 and require Source ratification.

**Deferral rationale**: Feature 002 specifies the policy CI must obey
(verifies-not-ratifies invariant; mechanical validation only; CI
evidence linkage to SDLC transition T17). Wiring `.github/` is a
separate batch with its own ratification and is gated on Feature 002's
canonical docs landing first.

## d. Feature 004 — independent review / QA agent evidence (scope summary)

**Status**: Deferred. Not yet specced.

Feature 004 will instantiate the governed identities Feature 002 names
but does not implement:

- Codex reviewer identity record per Feature 001 identity contract.
- QA agent identity record per Feature 001 identity contract.
- security agent identity record per Feature 001 identity contract.
- Review evidence schema; QA evidence schema; security finding record
  schema.
- Review gate definition; the rule that review evidence is not
  ratification for privileged classes (already invariant per Feature
  002 FR-013, FR-017).

**Deferral rationale**: Feature 002 names these roles in the
actor/tool ownership matrix with presence category "named in the
operating model; governed identity record deferred." Instantiating
their identity records and evidence schemas requires a separate spec
and ratification, since identity is itself a privileged mutation class.

## e. Feature 005 — Parallel Controller Orchestration (PCO) (scope summary)

**Status**: In progress. Slice 0 (Active-Work Ledger) is the first
coordination-substrate slice; later slices remain deferred.

Feature 005 establishes the parallel-controller orchestration
substrate that lets multiple Source-ratified Controllers coordinate
isolated lanes of work without colliding on worktrees, branches, or
Assignment Envelopes, and that, in later slices, automates the
dispatcher / worktree / sandbox runtime previously planned under
Feature 005. PCO is layered onto, not in place of, the
one-driver-per-worktree rule from
[`../architecture/parallel-agent-development-model.md`](../architecture/parallel-agent-development-model.md).

Slice plan:

1. **Slice 0 — Active-Work Ledger** *(merged on `main` via PR #52,
   merge commit `dab1ac9`)*. Adds the ledger record schema
   (`schemas/active-work-ledger.schema.yaml`), the prose protocol
   ([`../operations/ACTIVE_WORK_LEDGER_PROTOCOL.md`](../operations/ACTIVE_WORK_LEDGER_PROTOCOL.md)),
   the architecture doc
   ([`../architecture/parallel-controller-orchestration.md`](../architecture/parallel-controller-orchestration.md)),
   and a validator skeleton (`active_work_ledger_schema`). Records
   and validates only; does not yet enforce multi-controller
   execution. Spec:
   [`../../specs/005-pco-parallel-controller-orchestration/spec.md`](../../specs/005-pco-parallel-controller-orchestration/spec.md).
1.5. **Slice 0.5 — Completion Report Substrate** *(in progress,
   this batch)*. Adds the completion-report record schema
   (`schemas/completion-report.schema.yaml`), the prose protocol
   ([`../operations/COMPLETION_REPORT_PROTOCOL.md`](../operations/COMPLETION_REPORT_PROTOCOL.md)),
   per-class Markdown/YAML templates under
   `templates/hermes/completion-reports/`, well-formed/malformed
   examples under `examples/well-formed/completion-reports/` and
   `examples/malformed/completion-reports/`, and three validator
   checks (`completion_report_schema` CR-001,
   `completion_report_required_for_envelope` CR-002,
   `completion_report_terminal_sections` CR-003 warn-only).
   Additively extends the Active-Work Ledger schema with four new
   event kinds (`gate_opened`, `gate_closed`,
   `completion_report_emitted`, `gate_blocked`) under
   `schema_version: "2"`. Records and validates only; the Hermes
   final-answer / send-blocking runtime hook is reserved for the
   follow-on slice 0.5R. `requires: Slice 0`.
2. **Slice 1/2 — Conflict / Pre-Launch Validator** *(merged on
   `main` via PR #54, merge commit `6b0a19e`)*. Cross-record overlap
   detection: worktree-path collisions, lane uniqueness per
   controller, heartbeat monotonicity, event-id uniqueness within
   scope. Read-only refusal layer above Slice 0 schema records;
   does not allocate worktrees or launch panes.
2.5A. **Slice 2A — Worktree Lease substrate** *(merged on `main`
   via merge commit `6660b90`)*. Adds the tracked Worktree Lease
   record schema (`schemas/worktree-lease.schema.yaml`), the prose
   protocol
   ([`../operations/WORKTREE_LEASE_PROTOCOL.md`](../operations/WORKTREE_LEASE_PROTOCOL.md)),
   and additive `active_work_ledger_conflicts` refusal predicates
   (`PCO-021` claim-requires-live-lease, `PCO-022`
   cross-controller lease conflict, `PCO-023` lease invalid
   record). Substrate-only; runtime allocation deferred to Slice
   2R; identity hardening deferred to Slice 2.5. Gated on
   discovery of at least one valid lease record so trees with zero
   lease records preserve Slice 1/2 behavior unchanged.
2.5B. **Slice 2.5 — Controller Identity Substrate** *(next
   ratified gate; paired with Slice 2R)*. Adds a tracked
   controller-key record schema (provisionally
   `schemas/controller-key.schema.yaml`), an additive lease
   signature field under
   `schemas/worktree-lease.schema.yaml`
   `schema_version: "2"`, and a new
   `worktree_lease_signature` validator predicate (`PCO-024`) that
   refuses unsigned or mis-signed leases when at least one
   controller-key record exists. Backward-compatibility floor:
   trees with zero key records preserve Slice 2A behavior
   unchanged. Key custody, key location, and signature
   serialization remain open Source decisions per the spec's Open
   Source Decisions section. `requires: Slice 2A`.
3. **Slice 2R — Worktree Allocator Runtime** *(implemented in this
   gate; paired with Slice 2.5)*. Ships `pco-allocate` and
   `pco-release` CLI; atomic `git worktree add` + lease + claim +
   event flow under the lane's advisory lock;
   claim-writes-only-under-held-lease runtime enforcement (PCO-029);
   callable pane-launch guard (PCO-030); root checkout invariant
   preservation (PCO-031); Slice 2R boundary statement (PCO-032).
   Converts the existing Slice 1/2 + 2A read/validate/refuse
   substrate into runtime block. Subsumes the Feature 005
   worktree-lifecycle automation line item. Does NOT introduce pane
   registry, side-effect ledger, fan-in, integration queue, tracker
   connector, or runtime autonomy expansion. Prose contract:
   [`docs/operations/WORKTREE_ALLOCATOR_PROTOCOL.md`](../operations/WORKTREE_ALLOCATOR_PROTOCOL.md).
   `requires: Slice 2A, Slice 2.5`.
3.5. **Slice 2I — Worker Isolation Runtime** *(spec amendment
   authored; runtime deferred; bridges between Slice 2.5 + 2R
   authoring and Slice 2.5 + 2R implementation)*. Sibling/bridge
   slice that introduces a worker-container substrate beneath the
   visible tmux pane: a tracked worker-container policy record, a
   tracked container-instance record, a mount manifest, a
   secret-grant manifest (no values), a network policy record, an
   artifact collection manifest, termination / garbage-collection
   event records, the kernel/syscall verb set
   (`allocate_worker`, `mount_workspace`, `grant_path_capability`,
   `inject_secret`, `set_network_policy`, `run_command`,
   `collect_artifacts`, `terminate_worker`,
   `garbage_collect_worker`), six substrate-level refusal
   predicates (`PCO-040` through `PCO-045`), and a default-deny
   safety floor (read-only mounts; no host home mount; no host
   SSH/GitHub/model-provider credentials by default; no container
   engine socket inside a worker container; role-specific egress;
   redaction/revocation of secrets). Roles are distinguished:
   `architect_research`, `implementer`, `verification`. Container
   engine (rootless Podman vs. rootless Docker), image baseline,
   credential broker, egress enforcement primitive, image
   separation by role, mount-grant authority, and a per-container
   ephemeral controller-key amendment to Slice 2.5's OSD-1 are
   recorded as Open Source Decisions (OSD-I-1 through OSD-I-7
   plus the OSD-1 amendment). Spec amendment lives at
   [`../../specs/005-pco-parallel-controller-orchestration/worker-isolation-runtime.md`](../../specs/005-pco-parallel-controller-orchestration/worker-isolation-runtime.md).
   Slice 2I is split into **Slice 2I-S** (substrate; this gate
   authors the contracts) and **Slice 2I-R** (runtime; engine
   wiring, allocator extension between PCO-027 steps 5 and 6,
   credential broker, egress primitive — separately ratified and
   deferred). Slice 2I-S does NOT amend `PCO-024` through
   `PCO-032`; does NOT containerize the Controller (deferred to
   no earlier than after Slice 6, per OSD-I-3); does NOT pull,
   build, run, or inspect any container image; does NOT mutate
   Hermes runtime/profile/config/hook/MCP/model-provider
   surfaces; and does NOT expand Phase 1 / Phase 2 autonomy.
   `requires: Slice 2A, Slice 2.5, Slice 2R` (for sibling
   ordering; Slice 2I-S authoring does not block Slice 2.5 + 2R
   authoring, but Slice 2.5 + 2R *implementation* should not
   proceed before Slice 2I-S is ratified and OSD-1 is resolved
   compatibly with §f.3 of the Slice 2I-S amendment).
4. **Slice 3 — Pane Registry.** Visible-pane identity records — which
   Architect/Implementer pane is bound to which claim, on which host.
   Pane identity binds to a container-instance id (when present) per
   the Slice 2I-S substrate, so Slice 3 should be authored against
   Slice 2I-S to avoid a v2 migration.
5. **Slice 4 — Side-Effect Ledger.** Tracks externally observable
   side effects per lane (CI runs, deploys, GitHub state mutations).
6. **Slice 5 — `pco-fanin`.** Integration verification under
   multi-lane authorship; reconstructs the integrated state from
   tracked artifacts and validator output, not from lane self-report.
7. **Slice 6 — Integration Queue.** Serialized canonical-branch
   landing order across lanes; Source-ratified. Subsumes the
   conflict-detection-and-routing line item previously planned for
   Feature 005.

The previously-planned dispatcher / worktree / sandbox runtime work
(Hermes dispatcher, worktree lifecycle automation, sandboxing for
safe parallel runtime, taxonomy-routed conflict detection) is
preserved as later-slice scope under PCO. Each later slice keeps the
substrate-before-automation discipline: protocol and validator first,
runtime tooling after.

**Team-mode forward reference**: Slices 0 through 6 cover
**local-solo-developer** parallel-Controller substrate and runtime.
The paired Slice 2.5 + Slice 2R gate is local-solo-developer runtime
hardening, not team-mode operation. Multi-developer /
cross-workstation operation requires additional, separately ratified
workstreams that this roadmap names but does not yet spec:

- **Project Coordination Ledger (PCL)** — provisional Feature 007,
  team-mode equivalent of the Active-Work Ledger, tracked in the
  repository (not under `.hermes/`).
- **Source-Host & Tracker Connectors** — provisional Feature 008,
  governed mirrors for GitHub Issues / Jira / Linear. **Tracker and
  GitHub-issue entries remain mirrors, not canonical authority**,
  unless Source later ratifies a different team-mode design.
- **Distributed Identity Substrate** — provisional Feature 009,
  developer + workstation + Controller key binding that
  productionizes Slice 2.5's per-host or per-tenant key into a
  multi-developer-aware identity model.

These workstreams are named here as forward references only; no
implementation is promised by this ROADMAP entry, and the Slice
2.5 + 2R authoring gate does not authorize them.

**Deferral rationale**: Feature 002 specifies the manual protocol the
orchestration substrate must obey. Building automation before the
manual coordination substrate is rehearsed risks freezing a wrong
protocol into code. Slice 0 is the substrate; later slices add
automation on top of it.

## f. Feature 006 — release / deployment governance (scope summary)

**Status**: Deferred. Not yet specced.

Feature 006 will own the release/deploy automation Feature 002
specifies but does not author:

- Release agent identity record per Feature 001 identity contract.
- Release records, deploy attestations, rollback evidence records.
- GitHub environments and environment gates.
- Source-approved deploy gates for SDLC transitions T22 (Deployment
  Approved), T23 (Deployment Complete), and T24 (Post-release Evidence
  Recorded).
- Release-readiness checklist.

The `deploy` mutation class remains Source-only per Feature 001 FR-008
regardless of Feature 006 automation. Feature 006 implements the
execution surface; ratification of the deploy mutation remains
Source's.

**Deferral rationale**: No deploy targets currently exist; building
deploy automation before deploy targets and deploy governance are
ratified would produce automation looking for a problem.

## g. v1.0 — end-to-end governed agentic SDLC loop (integration target)

**Status**: Integration target.

v1.0 is the integration target the operating model points toward, not
a feature in itself. It is reached when Features 001 through 006 have
landed and together implement the full SDLC state machine end-to-end
with every privileged gate human-ratified and every non-privileged
gate eligible for ratified Phase 2 expansion under a future policy.

Concretely, v1.0 requires:

- Feature 001 substrate ratified and validator passing on the
  reference tenant.
- Feature 002 canonical document set authored and ratified (Slice A of
  Sprint 0 Execution).
- Feature 003 CI governance live with PR validation evidence.
- Feature 004 independent reviewer / QA / security identities and
  evidence schemas live.
- Feature 005 dispatch / worktree / sandbox runtime in production for
  manually approved batches.
- Feature 006 release / deployment governance live; deploy gates
  Source-approved.
- Sprint 0 exit gates 1–12 satisfied (per
  [`../../specs/sprint-0-minimum-viable-delivery-system/README.md`](../../specs/sprint-0-minimum-viable-delivery-system/README.md)
  §4).

## h. Per-feature deferral rationale (summary)

| Feature | Owns | Deferred from Feature 002 because |
|---|---|---|
| 003 | `.github/` workflows, PR templates, branch protection, CI checks | Feature 002 is specification-only at the operating-model layer; wiring CI is a privileged `governance`/`security`/`deploy` mutation that requires its own spec/plan/tasks triple. |
| 004 | Codex / QA / security identity records and evidence schemas | Identity is a privileged mutation class (Feature 001 FR-008); each governed identity requires its own ratified spec. Feature 002 names the roles and reserves their surfaces. |
| 005 | Parallel Controller Orchestration (PCO): active-work ledger, conflict validator, worktree allocator, pane registry, side-effect ledger, `pco-fanin`, integration queue, and the dispatcher / sandbox runtime previously planned under Feature 005. | Feature 002 specifies the manual protocol the orchestration substrate must obey; building automation before the manual coordination substrate is rehearsed risks freezing a wrong protocol into code. |
| 006 | Release records, deploy attestations, rollback evidence, GitHub environments, Source-approved deploy gates | The `deploy` mutation class is Source-only per Feature 001 FR-008; deploy targets do not yet exist. |

Phase 2 autonomy expansion is OUT OF SCOPE for any of Features 002
through 006 absent a separately ratified amendment to Feature 002's
Phase 1 / Phase 2 boundary.

## Acceptance posture for this document

This ROADMAP.md satisfies Feature 002 Canonical Document Specification
#3: every feature 001 through 006 has a scope summary and a deferral
rationale; v1.0 is explicitly named as the integration target;
sequencing matches Feature 002 FR-025 deferrals; no roadmap entry
promises automation Feature 002 does not enable.
