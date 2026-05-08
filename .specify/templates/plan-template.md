# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]  
**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]  
**Storage**: [if applicable, e.g., PostgreSQL, CoreData, files or N/A]  
**Testing**: [e.g., pytest, XCTest, cargo test or NEEDS CLARIFICATION]  
**Target Platform**: [e.g., Linux server, iOS 15+, WASM or NEEDS CLARIFICATION]
**Project Type**: [e.g., library/cli/web-service/mobile-app/compiler/desktop-app or NEEDS CLARIFICATION]  
**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]  
**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]  
**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify this plan against `.specify/memory/constitution.md`. For each gate
below, record PASS / FAIL / N/A with a one-line justification.

- **PASS**: the plan satisfies the gate.
- **FAIL**: the plan violates the constitution and is blocked until revised or
  until a Source-approved constitutional amendment changes the rule.
- **N/A**: the gate does not apply to this plan, or the relevant Creator
  Engine schema/validator has not been defined yet. N/A requires a concrete
  explanation and MUST NOT be used to bypass an already-defined rule.

- [ ] **I. Spec-First**: Approved spec exists, or this is explicitly approved
  bootstrap governance setup; this plan does not introduce scope absent from
  the spec or approved bootstrap scope.
- [ ] **II. Repo-Native (v0.1)**: Plan produces only files/schemas/examples/
  validators in this repo; no hosted control plane or external state store.
- [ ] **III. Explicit Agent Identity**: Plan identifies the tenant, source
  host, actor identity, runtime/tool, role, and authority context for any
  agent-authored execution it describes. Before the identity schema exists,
  provide these fields as plain text; do not mark this N/A for agent-authored
  work.
- [ ] **IV. Mutation-Class Governance**: Plan declares the mutation class(es)
  involved and the actions each class permits. Before the mutation-class
  schema exists, provide the class and permitted action as plain text; do not
  mark this N/A for executable work.
- [ ] **V. Author/Approver Separation**: Plan does not assume the author may
  also approve or ratify; reviewer/ratifier roles are distinct from author.
- [ ] **VI. Human Ratification**: Any merge, deploy, governance, security, or
  identity step in this plan is explicitly gated on human/role ratification.
- [ ] **VII. Verification Over Claims**: Plan defines concrete verification
  evidence (tests, checks, review findings) for each completion claim.
- [ ] **VIII. Attestation**: Plan describes how the resulting attestation
  record will be produced and where it will live in the repo. Before the
  attestation schema exists, only bootstrap or contract-definition work may
  mark schema-specific attestation as N/A, and the plan MUST still record
  bootstrap evidence in repository-visible artifacts.
- [ ] **IX. LIMITLESS as Dogfood**: No tenant-specific assumption is hard-coded
  into substrate artifacts; tenant data lives in fixtures.
- [ ] **X. Spec Kit Compatibility**: Plan does not break vanilla Spec-Kit
  readability of `spec.md` / `plan.md` / `tasks.md`.
- [ ] **XI. YAGNI (v0.1)**: Plan introduces no coordination/drift/dashboard/
  hosted-policy/multi-tenant-SaaS behavior as part of v0.1. Any such work is
  outside the v0.1 charter and requires a separate Source-approved charter or
  version change before it may be planned.
- [ ] **XII. Security & Privacy**: Plan declares security/privacy posture and
  does not introduce public/NDA-visible export pathways unless redaction gates
  are explicitly defined and enforced.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
