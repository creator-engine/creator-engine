# Sprint 0 Execution: Minimum Viable Delivery System

**Status**: Source-approved Sprint 0 execution sequence

**Created**: 2026-05-11

**Applies to**: Creator Engine development after the merged governance-substrate baseline (Feature 001 governance-substrate work: `feat: add Creator Engine governance substrate and SDLC operating model`)

**Decision**: Source approved **Option C — Minimum Viable Delivery System Sprint 0**.

**Purpose**: Retroactively complete the minimum Sprint 0 / Delivery Readiness system needed for safe, repeatable implementation of Creator Engine itself. This artifact is not a replacement for Feature 002 and does not author the canonical document bodies; it sequences the work required to make Sprint 0 real.

## 1. Rationale

Creator Engine began governed implementation before a full enterprise Sprint 0 / Delivery Readiness phase existed.

Feature 001 delivered the governance substrate: contracts, schemas, validator scaffolding, examples, and the first authority/mutation model.

Feature 002 delivered a specification-only operating model: it defined the canonical document set and agentic SDLC model, but intentionally did not author the canonical document bodies, CI/CD workflows, governed review identities, dispatcher/runtime, or release/deploy automation.

This document corrects the sequencing gap. It does not claim that Sprint 0 is already complete. Sprint 0 is not complete merely because the canonical documents exist; documentation is only Slice A of the minimum delivery system. This document defines the bounded execution sequence required to produce that system before normal feature implementation resumes.

## 2. Source-of-Truth Hierarchy

This document is an execution-sequencing artifact. It is subordinate to:

1. `.specify/memory/constitution.md`
2. Feature 001 governance substrate artifacts under `specs/001-v0-1-governance-substrate/`, `docs/contracts/`, `schemas/`, `templates/`, `validators/`, and `examples/`
3. Feature 002 operating-model specification at `specs/002-canonical-docs-and-operating-model/spec.md`
4. This Sprint 0 Execution document

If this document conflicts with Feature 001 or Feature 002, Feature 001/002 control and this document must be corrected.

## 3. Non-Goals

Sprint 0 Execution must not become an unbounded enterprise overbuild.

The minimum viable delivery system does **not** require the following before normal feature work can resume:

- production deployment automation
- cloud environments that do not yet exist
- full infrastructure-as-code
- observability dashboards for services that do not yet run
- autonomous dispatcher daemon
- autonomous QA/release agent runtime
- complex release trains
- external Jira integration

The goal is not maximum process. The goal is enough delivery structure to make subsequent implementation safe, repeatable, reviewable, and roadmap-driven.

## 4. Sprint 0 Exit Gate

Creator Engine must not claim Sprint 0 / Delivery Readiness complete until all minimum gates below are satisfied:

1. The 17 Feature 002 canonical documents exist and satisfy their Feature 002 acceptance criteria.
2. A repo-native roadmap/backlog/Kanban equivalent exists and can answer “what is next?” after every merge.
3. A post-merge next-task protocol is documented and used.
4. Baseline PR validation exists through GitHub Actions, or Source ratifies a temporary repo-visible exception.
5. PR template and review policy exist.
6. Branch protection is active, or a repo-visible manual protection policy is ratified until GitHub settings are applied.
7. Source, Hermes/Nefarious, Claude Code, and Codex/reviewer roles are governed enough to execute the next feature safely.
8. Assignment Envelope template exists and has been dry-run at least once.
9. Worktree/branch naming and one-driver-per-worktree rules are documented.
10. QA/review evidence format exists.
11. Release/merge/deploy governance is documented, even where deploy automation remains deferred.
12. Feature 003+ work is sequenced with dependencies, stop conditions, and acceptance gates.

Until all gates pass, Creator Engine is in **Sprint 0 Execution**, not normal feature iteration.

## 5. Execution Sequence

### Slice A — Canonical Documentation

**Goal**: Author the canonical documentation set specified by Feature 002.

**Outputs**:

- `README.md`
- `docs/product/PRD.md`
- `docs/product/ROADMAP.md`
- `docs/product/REQUIREMENTS.md`
- `docs/architecture/SAD.md`
- `docs/architecture/agentic-sdlc-operating-model.md`
- `docs/architecture/integration-map.md`
- `docs/architecture/agent-interaction-model.md`
- `docs/architecture/parallel-agent-development-model.md`
- `docs/governance/AUTHORITY_AND_RATIFICATION_MODEL.md`
- `docs/governance/MUTATION_CLASS_MODEL.md`
- `docs/governance/ATTESTATION_MODEL.md`
- `docs/quality/QA_STRATEGY.md`
- `docs/quality/TESTING_STRATEGY.md`
- `docs/devops/CI_CD_STRATEGY.md`
- `docs/devops/RELEASE_AND_DEPLOYMENT_STRATEGY.md`
- `docs/security/SECURITY_MODEL.md`

**Acceptance**:

- Each document satisfies the required purpose, required sections, source-of-truth relationship, and acceptance criteria specified by Feature 002.
- Documents summarize and reference Feature 001 contracts where applicable; they do not redefine Feature 001 contracts.
- Deferrals to future implementation remain explicit.
- No `.github/`, CI workflow, identity record, dispatcher runtime, or release/deploy automation is implemented in Slice A unless separately ratified by Source.

### Slice B — Roadmap, Backlog, Kanban, and Next-Task Protocol

**Goal**: Create the repo-native equivalent of the enterprise Jira/Kanban delivery system.

**Outputs**:

- Roadmap and milestone sequencing for Sprint 0 completion and post-Sprint-0 work.
- Epic/story/task hierarchy or equivalent markdown backlog.
- Dependency map and risk register.
- Definition of Ready and Definition of Done for Creator Engine work items.
- Post-merge next-task protocol.

**Acceptance**:

- After any merge, the roadmap/backlog can identify the next recommended task without improvisation.
- Every future work item has a clear parent milestone/epic/slice and acceptance gate.
- The post-merge protocol is mandatory for Nefarious completion reports.

### Slice C — Thin GitHub / CI / PR Governance

**Goal**: Establish minimum repository-level verification and review controls.

**Outputs**:

- `.github/workflows/` baseline validation workflow.
- PR template.
- Review policy and/or CODEOWNERS policy where appropriate.
- Branch protection policy/checklist, plus applied branch protection if Source authorizes GitHub settings mutation.
- CI evidence rule: CI verifies but never ratifies.

**Acceptance**:

- Pull requests receive automated validation evidence or an explicitly ratified temporary exception.
- PRs expose scope, validation evidence, review evidence, deferrals, and Source-ratification requirements.
- Branch protection policy is documented; any live GitHub settings mutation is separately ratified by Source.

### Slice D — Minimum Review / QA / Identity Governance

**Goal**: Establish enough governed review and QA evidence to continue implementation safely.

**Outputs**:

- Codex/reviewer role record or equivalent governed reviewer identity artifact.
- QA/review evidence template.
- Review gate definition.
- Rule that review evidence is not Source ratification.

**Acceptance**:

- Every future mergeable unit has independent review evidence unless Source explicitly waives it.
- Reviewer identity and authority are documented.
- Privileged mutation classes still require Source ratification.

### Slice E — Manual Assignment Envelope and Worktree Runtime Protocol

**Goal**: Establish the manual protocol that future dispatcher/runtime automation must preserve.

**Outputs**:

- Assignment Envelope template.
- Worktree naming convention.
- Branch naming convention.
- One-driver-per-worktree rule.
- Envelope consumption checklist.
- Scope audit checklist.
- Dry-run evidence for at least one assignment envelope.

**Acceptance**:

- A Hermes/Nefarious operator can assign a bounded batch to Claude Code without ambiguity.
- Claude Code can consume the envelope, execute within scope, and stop at declared stop conditions.
- Parallel work is allowed only through isolated branches/worktrees with non-overlapping envelopes or declared dependencies.

### Slice F — Release / Deploy Governance Policy

**Goal**: Define release, merge, deployment, rollback, and post-release evidence policy before any production-like deployment automation exists.

**Outputs**:

- Release candidate checklist.
- Merge approval checklist.
- Deployment approval policy.
- Rollback/evidence expectations.
- Explicit deploy mutation ratification rule.
- Statement of currently absent deployment targets/environments, if applicable.

**Acceptance**:

- Creator Engine can distinguish merge, release candidate, deploy approval, deploy execution, and post-release evidence.
- No agent can deploy without Source-ratified authority.
- Release/deploy automation remains deferred until this policy is satisfied and a later implementation slice is ratified.

## 6. Relationship to Future Features

The previous labels remain conceptually useful, but during Sprint 0 Execution they are treated as delivery-readiness slices, not ordinary product expansion.

- Feature 002 implementation is Slice A.
- Feature 003 concepts are partially pulled into Slice C as thin CI/PR governance.
- Feature 004 concepts are partially pulled into Slice D as minimum review/QA identity governance.
- Feature 005 concepts are partially pulled into Slice E as a manual assignment-envelope/worktree protocol.
- Feature 006 concepts are partially pulled into Slice F as release/deploy governance policy.

Full automation beyond the minimum viable delivery system remains deferred until Sprint 0 gates pass and Source ratifies the next feature scope.

## 7. Post-Merge Next-Task Protocol

Every merge completion report must include:

1. Merge identification: PR, branch, target, merge commit, feature/slice.
2. Scope summary: what changed and what intentionally did not change.
3. Validation evidence: commands, checks, CI, skipped checks, and rationale.
4. Governance evidence: mutation classes, ratification, attestation/review evidence.
5. Scope audit: changed paths and prohibited surfaces check.
6. Documentation impact: canonical docs or source-of-truth changes.
7. Deferred work: explicit deferrals and owning future slice/feature.
8. Readiness impact: which Sprint 0 gate advanced or remains blocked.
9. Immediate next-task recommendation: one recommended next task and why.
10. Cleanup state: branch/worktree status and whether cleanup requires Source approval.

A merge report that does not state the next task is incomplete.

## 8. Current Next Task

Current state after the merged governance-substrate baseline (the v0.1 governance substrate):

- Feature 001 governance substrate is merged.
- Feature 002 specification-only operating model is merged.
- Sprint 0 / Delivery Readiness is not complete.
- The canonical documentation directories and `.github/` are absent.

The next task is:

**Sprint 0 Execution Slice A — Author the Feature 002 canonical documentation set.**

Before Slice A implementation begins, Nefarious should prepare an architect/engineer handoff that points Claude Code to Feature 002, this document, Feature 001 contracts, and the acceptance boundaries above.

## 9. Stop Conditions

Stop and return to Source for decision if any Slice A–F work requires:

- changing Feature 001 contract semantics
- changing Feature 002 acceptance criteria
- creating or changing `.github/` before Slice C
- changing live GitHub repository settings
- creating new governed identities beyond the minimum review role
- implementing dispatcher/runtime automation instead of a manual protocol
- implementing deployment automation
- weakening ratification, attestation, redaction, security, or identity gates
- expanding scope beyond minimum viable delivery readiness
