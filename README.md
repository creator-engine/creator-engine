# Creator Engine

## What Creator Engine is

Creator Engine is a repo-native agentic SDLC governance substrate. It
makes agent-authored software work auditable, spec-driven,
identity-aware, mutation-class governed, verified by evidence, and
ratified by explicit authority rules. v1.0 is the integration target:
an end-to-end governed agentic SDLC loop with every privileged gate
human-ratified.

## v0.1 scope

v0.1 ships only files inside a git repository. Two layers compose it:

- **Feature 001 — governance substrate** (merged). Identity schema,
  mutation-class taxonomy with nine baseline classes, reserved-action
  vocabulary, authority matrix, attestation / ratification / redaction
  record formats, Spec Kit wrapper sidecars, Definition of Ready and
  Definition of Done, redaction gate policy, and an offline validator
  runnable from a fresh `git clone`.
- **Feature 002 — operating model**. The 25-state SDLC machine with
  24 transitions, the Assignment Envelope contract, the
  `/speckit-implement` policy, the actor/tool ownership matrix, the
  parallel-agent development model, the conflict taxonomy, and the
  Phase 1 / Phase 2 boundary. Feature 002 specifies the canonical
  document set; the bodies below are authored in Sprint 0 Execution
  Slice A.

Phase 2 autonomy (low-risk auto-merge, autonomous batch-pulling) and
v1.0 end-to-end automation are integration targets, not v0.1
deliverables.

## Repository layout

- `.specify/memory/constitution.md` — highest-authority governance
  document.
- `specs/` — Spec Kit feature specifications, including Feature 001
  (governance substrate), Feature 002 (canonical docs and operating
  model), and the Sprint 0 minimum viable delivery system note.
- `docs/contracts/` — Feature 001 governance contract documents.
- `docs/product/`, `docs/architecture/`, `docs/governance/`,
  `docs/quality/`, `docs/devops/`, `docs/security/` — the canonical
  Creator Engine document set indexed below.
- `docs/operations/` — operational protocol documentation (e.g.,
  `docs/operations/session-continuity-protocol.md`). These are
  operational protocols, not part of the 17-document canonical set
  indexed below.
- `schemas/`, `templates/`, `validators/`, `examples/`, `tenants/` —
  Feature 001 substrate artifacts and tenant fixtures.
- `.hermes/` — Session continuity protocol and state for the operator.
- `validators/README.md` — substrate validator quickstart.

See [`validators/README.md`](./validators/README.md) for the offline
install and validator quickstart.

## Canonical document index

The canonical document index — the canonical Creator Engine document
set — is exactly these 17 documents (Feature 002 FR-022):

1. [`README.md`](./README.md) — this orientation document.
2. [`docs/product/PRD.md`](./docs/product/PRD.md) — product vision,
   target tenants, problem statement, value proposition, primary use
   cases, non-goals, success metrics, version-scope summaries.
3. [`docs/product/ROADMAP.md`](./docs/product/ROADMAP.md) — Features
   001–006 scope summaries and v1.0 integration target.
4. [`docs/product/REQUIREMENTS.md`](./docs/product/REQUIREMENTS.md) —
   product requirements catalog with traceability to Feature 001/002.
5. [`docs/architecture/SAD.md`](./docs/architecture/SAD.md) — system
   architecture: components, data flows, storage, trust boundaries,
   extension points.
6. [`docs/architecture/agentic-sdlc-operating-model.md`](./docs/architecture/agentic-sdlc-operating-model.md)
   — the 25-state SDLC machine, transition matrix, Phase 1/2 boundary,
   `/speckit-implement` policy, and Assignment Envelope linkage.
7. [`docs/architecture/integration-map.md`](./docs/architecture/integration-map.md)
   — boundaries with Spec Kit, GitHub, CI, and trackers.
8. [`docs/architecture/agent-interaction-model.md`](./docs/architecture/agent-interaction-model.md)
   — actor-to-actor interaction patterns, envelope handoff sequence,
   escalation paths.
9. [`docs/architecture/parallel-agent-development-model.md`](./docs/architecture/parallel-agent-development-model.md)
   — one-driver-per-worktree rule, parallel-pair pattern, conflict
   taxonomy.
10. [`docs/governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](./docs/governance/AUTHORITY_AND_RATIFICATION_MODEL.md)
    — authority matrix summary, ratifier taxonomy, SDLC transition →
    ratifier link table.
11. [`docs/governance/MUTATION_CLASS_MODEL.md`](./docs/governance/MUTATION_CLASS_MODEL.md)
    — baseline classes, reserved-action vocabulary, privileged-class
    rules.
12. [`docs/governance/ATTESTATION_MODEL.md`](./docs/governance/ATTESTATION_MODEL.md)
    — attestation record fields, storage, SDLC linkage, bootstrap
    grandfathering.
13. [`docs/quality/QA_STRATEGY.md`](./docs/quality/QA_STRATEGY.md) —
    testing levels per mutation class; QA agent role; deferrals.
14. [`docs/quality/TESTING_STRATEGY.md`](./docs/quality/TESTING_STRATEGY.md)
    — engineering testing practices, validator self-tests, evidence
    capture, self-claim rejection invariant.
15. [`docs/devops/CI_CD_STRATEGY.md`](./docs/devops/CI_CD_STRATEGY.md)
    — verifies-not-ratifies invariant, required CI checks, branch
    protection policy summary, Feature 003 deferral.
16. [`docs/devops/RELEASE_AND_DEPLOYMENT_STRATEGY.md`](./docs/devops/RELEASE_AND_DEPLOYMENT_STRATEGY.md)
    — environment taxonomy, deploy-as-privileged-class rule, rollback
    evidence, Feature 006 deferral.
17. [`docs/security/SECURITY_MODEL.md`](./docs/security/SECURITY_MODEL.md)
    — security as design constraint, redaction gate summary, secrets
    and rotation policy, escalation paths.

## Source of truth notice

The constitution at
[`.specify/memory/constitution.md`](./.specify/memory/constitution.md)
is the highest-authority document for agent-authored work.

The
[Feature 002 source-of-truth hierarchy](./specs/002-canonical-docs-and-operating-model/spec.md#fr-019)
(FR-019) is:
constitution > Feature 001 governance substrate (ratified) >
Feature 002 canonical docs (above) > tenant fixtures
(`tenants/<name>/`) > working notes and handoffs.

Amendments to the constitution, the Feature 001 substrate, or the
Feature 002 operating model are themselves Creator-Engine-governed
mutations: a spec/plan/tasks triple under explicit Source approval,
versioned per the constitution's Governance section.
