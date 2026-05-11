# Creator Engine Integration Map

**Status**: Canonical. Authored under Sprint 0 Execution Slice A.

**Source-of-truth relationship**: REFERENCE. This document defers to
the Feature 001 wrapper sidecar contracts under
[`../../specs/001-v0-1-governance-substrate/`](../../specs/001-v0-1-governance-substrate/)
and to the operating model in
[`./agentic-sdlc-operating-model.md`](./agentic-sdlc-operating-model.md).
Where this map and the source spec at
`specs/002-canonical-docs-and-operating-model/spec.md` disagree, the
source spec wins.

## a. Spec Kit integration boundary

**Boundary**: Creator Engine wraps Spec Kit with adjacent YAML
sidecars; vanilla Spec Kit files remain byte-identical.

**What Creator Engine governs**:

- `spec.creator-engine.yml` — wrapper sidecar fields per Feature 001
  FR-009 and FR-012a.
- `plan.creator-engine.yml` — plan-level mutation-class summary per
  FR-012b.
- `tasks.creator-engine.yml` — task-level mutation class / action /
  evidence declarations per FR-012b; carries the
  `author_actor_id` entries that the candidate v0.1 FR-007 rule
  consumes (see
  [`../contracts/authority-matrix.md`](../contracts/authority-matrix.md)
  §Author definition).
- Spec Kit slash-command policy: `/speckit-specify`, `/speckit-clarify`,
  `/speckit-plan`, `/speckit-tasks`, `/speckit-implement`. After
  Feature 002 ratification, `/speckit-implement` is mandatory for
  Creator-Engine-governed implementation and MUST be invoked only
  inside a Hermes-authored Assignment Envelope (FR-009).

**What Spec Kit owns (external)**:

- The `spec.md`, `plan.md`, `tasks.md` body content and any native
  Spec Kit frontmatter or display fields. Creator Engine MUST NOT
  rename, restructure, or modify Spec Kit files; governance metadata
  lives only in the adjacent sidecars (FR-010).
- The Spec Kit slash-command implementations themselves.

**Spec-Kit-byte-identical invariant**: a `spec.md`/`plan.md`/`tasks.md`
file authored against vanilla Spec Kit MUST remain readable in any
plain Markdown reader and usable by vanilla Spec Kit tooling. This is
the v0.1 architectural commitment that preserves principle X (Spec
Kit compatibility).

**Deferral status**: integrated in v0.1 (Feature 001 ships the
wrapper sidecar schema and the validator that enforces it).

## b. GitHub integration boundary

**Boundary**: GitHub owns PR/merge mechanics; Creator Engine governs
what counts as a Creator-Engine-governed mutation and what evidence
must accompany merge.

**What Creator Engine governs**:

- The policy CI and PR templates must obey (verifies-not-ratifies
  invariant; mutation-class declarations; ratification record
  presence; attestation linkage). The policy is specified in
  [`../devops/CI_CD_STRATEGY.md`](../devops/CI_CD_STRATEGY.md).
- The Creator-Engine-classed mutation under review (the change being
  merged), distinct from the merge action itself.

**What GitHub owns (external)**:

- PR creation, comments, status checks, merges, release tags, and
  environments.
- Branch protection settings, PR template files, environment gates —
  all of which live under `.github/` and are deferred per below.

**Deferral status**: `.github/` workflows, PR template files, branch
protection (as live GitHub settings), and environment gates are
deferred to Feature 003 (branch protection / PR templates) and
Feature 006 (deploy environments). Feature 002 specifies the policy
GitHub must obey when those features land but does not author any
`.github/` content.

**Authority note**: branch protection, PR template, environment
gate, and merge-policy changes are themselves privileged
`governance`/`security`/`deploy` mutations per Feature 001 FR-008
and require Source ratification.

## c. CI integration boundary

**Boundary**: CI is mechanical validation only. CI verifies but does
NOT ratify.

**What Creator Engine governs**:

- The required CI checks (specified in
  [`../devops/CI_CD_STRATEGY.md`](../devops/CI_CD_STRATEGY.md) §b):
  tests, lint, typecheck, build, Creator Engine validator, schema
  validation.
- The verifies-not-ratifies invariant (FR-013).
- The CI evidence linkage to SDLC transition T17.
- The rule that CI policy or workflow changes are themselves
  privileged `governance`/`security`/`deploy` mutations (FR-008).

**What CI owns (external — once instantiated)**:

- Test execution, lint/typecheck execution, validator execution,
  status check reporting, run logs, and build artifacts.

**Deferral status**: CI workflow content (`.github/workflows/`), CI
check definitions, and CI infrastructure are deferred to Feature 003.
Feature 002 specifies the policy; Feature 003 wires the workflows.

**Authority note**: CI passing does not advance a privileged-class
mutation past T19 (Ratification Complete). CI output becomes
attestation evidence (T17) but never a ratification record.

## d. Tracker-agnostic work-item model

**Boundary**: Creator Engine treats the work-item layer as
tracker-agnostic.

**What Creator Engine governs**:

- The Spec Kit `tasks.md` plus `tasks.creator-engine.yml` sidecar is
  the canonical work-item record for Creator-Engine-governed
  batches.
- The Assignment Envelope's `approved_task_batch` field is the
  governed task identifier set per FR-005.
- Mutation-class declarations, permitted actions, and evidence
  requirements live in the tasks sidecar, not in an external
  tracker.

**What external trackers MAY own (optional)**:

- Tenant-specific roadmap / planning / sprint state in Linear, Jira,
  GitHub Projects, or another tracker.
- Cross-feature visibility surfaces (dashboards, reports).

**Deferral status**: external tracker integration is OUT OF SCOPE for
Creator Engine v0.1 per
[`../../specs/sprint-0-minimum-viable-delivery-system/README.md`](../../specs/sprint-0-minimum-viable-delivery-system/README.md)
§3 (Non-Goals). Tenants MAY integrate trackers locally; integration
is not specified by Creator Engine and produces no Creator Engine
governance artifacts.

**Authority note**: a tracker entry is not a substitute for a
Creator-Engine-governed spec, plan, or tasks artifact. Repo-visible
artifacts are canonical; tracker entries are non-canonical.

## e. Per-integration deferrals (Features 003–006)

This section is the consolidated deferral table for integrations.
Each row names the integration surface, the owning future feature,
and the rationale.

| Integration surface | Owning future feature | Why deferred |
|---|---|---|
| `.github/workflows/` baseline CI workflow | Feature 003 (GitHub CI Governance) | Feature 002 specifies the policy CI must obey; wiring CI is a separate ratified batch. CI policy changes are themselves privileged `governance`/`security`/`deploy` mutations per FR-008. |
| PR template file under `.github/` | Feature 003 | The PR template must surface scope, validation evidence, review evidence, mutation classes, deferrals, and Source ratification requirements; its content and its activation under GitHub are a ratified mutation. |
| Branch protection settings on GitHub | Feature 003 | Branch protection is a live GitHub setting change; itself a privileged `governance` mutation requiring Source ratification. |
| Codex reviewer identity record | Feature 004 (Independent Review / QA Agent Evidence) | Identity is privileged per FR-008; instantiating an agent identity requires its own ratified spec. Feature 002 names the role and reserves its surfaces. |
| QA agent identity record + QA evidence schema | Feature 004 | Same. |
| security agent identity record + security finding record schema | Feature 004 | Same. |
| Review findings record schema | Feature 004 | Review evidence is recorded but NEVER ratification for privileged classes; the schema must be ratified before review records become first-class governance artifacts. |
| Hermes dispatcher; worktree lifecycle automation; sandboxing; safe parallel runtime | Feature 005 (Dispatch / Worktree / Sandbox Runtime) | Feature 002 specifies the manual protocol the dispatcher must obey; automating before the protocol is rehearsed risks freezing a wrong contract. |
| Release agent identity record | Feature 006 (Release / Deployment Governance) | Same identity-class rationale as above; release identity is named with identity record deferred per FR-014. |
| Release records; deploy attestations; rollback evidence; post-release evidence records | Feature 006 | The `deploy` mutation class is Source-only per FR-008; deploy targets and their evidence chains await Feature 006's spec/plan/tasks triple. |
| GitHub environments; environment gates | Feature 006 | Live GitHub-settings mutations subject to Source ratification. |

Phase 2 autonomy policies (low-risk auto-merge, autonomous batch-
pulling) are themselves integration concerns that require a ratified
amendment to the Phase 1 / Phase 2 boundary per FR-028.

## f. Trust boundaries summary

The integration map surfaces three trust boundaries; the SAD's full
treatment lives in
[`./SAD.md`](./SAD.md) §e.

1. **Author/approver boundary (Feature 001 FR-007)**. The author of a
   mutation MUST NOT be the approving reviewer or ratifier of that
   same mutation. This boundary cuts across Spec Kit (sidecar
   author/consumer roles), GitHub (PR author vs reviewer), CI (CI is
   never a ratifier), and tracker (tracker entries cannot ratify).
2. **Substrate/tenant boundary (constitution Principle IX; Feature
   001 FR-024)**. Generic-contract paths — `docs/contracts/`,
   `schemas/`, `validators/`, `templates/` — MUST contain no
   tenant-specific identifiers. Tenant-specific values live only
   under `tenants/<name>/`. This boundary preserves portability
   across tenants and trackers.
3. **Verifies-not-ratifies boundary (Feature 002 FR-013)**. CI,
   agents, and any future automation MAY produce evidence but MUST
   NOT produce ratification records for privileged classes. This
   boundary survives integration with new CI providers, new
   trackers, and new agent runtimes.

## Acceptance posture for this document

This integration-map.md satisfies Feature 002 Canonical Document
Specification #8: every integration boundary row names ownership
(Creator Engine governs vs external owns) and deferral status;
`.github/` is explicitly listed as a Feature 003 deferral; Spec Kit
byte-identical invariant is stated; the trust boundaries summary
links to the SAD.
