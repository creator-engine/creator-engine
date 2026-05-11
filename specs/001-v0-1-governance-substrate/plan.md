# Implementation Plan: Creator Engine v0.1 Governance Substrate

**Branch**: `001-v0-1-governance-substrate` | **Date**: 2026-05-09 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-v0-1-governance-substrate/spec.md`

## Summary

Ship the v0.1 governance substrate as a set of repository artifacts only:
generic contract documents, YAML schemas, project-agnostic templates, a
machine-checkable validator runnable from a fresh `git clone` with no network,
example tenant fixtures (well-formed and deliberately malformed), and a
LIMITLESS dogfood fixture mapped onto those generic contracts. Creator Engine
governance metadata is carried in YAML sidecars adjacent to vanilla Spec Kit
files (`spec.creator-engine.yml`, `plan.creator-engine.yml`,
`tasks.creator-engine.yml`); Spec Kit Markdown files remain byte-identical to
vanilla Spec Kit. The substrate enforces a six-state spec lifecycle (`draft →
ready → in_progress → verified → ratified → done`) gated by Definition of
Ready, Definition of Done, author/approver separation, and an authority
matrix that names a ratifier per mutation class. Attestation, ratification,
and redaction records are stored as one-record-per-file YAML at
tenant-declared directory roots. The substrate's mutation-class taxonomy is a
mandatory baseline class set (`docs`, `code`, `schema`, `deploy`,
`governance`, `identity`, `security`, `attestation`, `redaction`); tenants
MAY overlay extension classes without redefining baseline semantics.

## Technical Context

**Language/Version**: Python 3.11 for the validator and any helper scripts.
Authored content (specs, contracts, schemas, templates, fixtures, examples) is
language-agnostic Markdown and YAML.

**Primary Dependencies**: `PyYAML` for YAML parsing, `jsonschema` (Draft
2020-12) for schema validation. Both are pure-Python, pinned in checked-in
`validators/requirements.txt`, and install offline from a checked-in
`validators/wheelhouse/` so fresh-clone validation and setup require no
network. No other runtime dependencies in v0.1.

**Storage**: Filesystem only. All governance artifacts (identity records,
sidecars, attestation/ratification/redaction records, fixtures, examples)
are repository files. No database, no external attestation store, no remote
policy service.

**Testing**: `pytest` for validator unit/integration tests. End-to-end
verification consists of running the validator against the bundled
well-formed and malformed example fixtures and asserting the documented
outcomes (FR-028, FR-029, SC-006). The validator's own `--check` invocation
on the bundled examples is the substrate's self-verification evidence
(FR-030, FR-031, SC-007).

**Target Platform**: Developer workstation with Python 3.11 and `git`. Must
work offline on a fresh `git clone`. No SaaS, no daemon, no hosted policy
engine.

**Project Type**: Repo-native governance substrate. Two artifact families:
(a) authored content — contracts, schemas, templates, fixtures, examples,
specs; (b) a small Python validator package and CLI under `validators/`.

**Performance Goals**: Validator completes a full pass on the bundled
example set in under 60 seconds on a developer workstation, with no network
(SC-007). v0.1 has no other performance targets; throughput, concurrency,
and runtime hot-path budgets are not in scope.

**Constraints**:
- Spec Kit `spec.md` / `plan.md` / `tasks.md` files MUST remain
  byte-identical to vanilla Spec Kit (FR-010, FR-012a, principle X). All
  Creator Engine fields live in adjacent `*.creator-engine.yml` sidecars.
- Generic contract documents under `docs/contracts/`, `schemas/`,
  `validators/`, `templates/` MUST contain zero LIMITLESS-specific
  identifiers from the canonical non-secret identifier list at
  `tenants/limitless/` (FR-024, FR-024a, SC-004).
- Attestation, ratification, and redaction records MUST be one-record-per-
  file YAML under tenant-declared directory roots
  (`attestation_storage_path`, `ratification_storage_path`,
  `redaction_storage_path`); filename convention
  `<date>-<record-subject-id>.yml` (FR-020a).
- Validator MUST be runnable from a fresh `git clone` with no external
  service calls (FR-026); validator errors MUST cite the violated contract
  clause (FR-027).
- v0.1 ships no public/NDA export workflow; the redaction gate is policy-
  and-validation only (US5, FR-019, principle XII).

**Scale/Scope**: One generic contract bundle (≈8–12 contract documents,
≈6–10 schemas, ≈4 templates), one project-agnostic example tenant under
`examples/` (well-formed and deliberately malformed pairs for each major
contract per FR-028/FR-029), one populated LIMITLESS dogfood fixture under
`tenants/limitless/`, one validator CLI. v0.1 is a single-feature delivery;
no multi-package monorepo, no plugin system.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Evaluated against `.specify/memory/constitution.md` v1.0.0.

- [x] **I. Spec-First**: PASS. `specs/001-v0-1-governance-substrate/spec.md`
  is approved (clarified 2026-05-09, status Draft pending ratification of this
  triple). This plan introduces no scope absent from that spec.
- [x] **II. Repo-Native (v0.1)**: PASS. Plan produces only files (contracts,
  schemas, templates, fixtures, examples), a Python validator package, and
  the substrate's own spec/plan/tasks. No hosted control plane, no external
  state store, no daemon.
- [x] **III. Explicit Agent Identity**: PASS (recorded as plain text per
  the constitution's pre-schema clause). Identity for this plan's own
  agent-authored execution: tenant=`creator-engine` (substrate self),
  source_host=GitHub, agent_app_slug=`limitless-agent[bot]` /
  agent_actor_id=Claude (Anthropic) under Spec Kit + Claude Code,
  runtime_tool=Claude Code CLI, role_category=`architect` for plan
  authorship, authority_context=Source-approved bootstrap of
  feature 001 against the v0.1 charter recorded in spec.md and the source
  plan referenced therein.
- [x] **IV. Mutation-Class Governance**: PASS (recorded as plain text per
  the constitution's pre-schema clause). Mutation class for this plan and
  the work it describes: `governance` (defines authority and ratification
  rules), `identity` (defines the identity record schema), `schema`
  (defines YAML schemas for sidecars and records), `attestation` (defines
  the attestation record format and the validator's attestation-linkage
  checks), and `docs` (generic contract documents and quickstart). Permitted
  actions for the agent under these classes during planning: propose, edit,
  attest. Reserved actions requiring explicit Source ratification: merge,
  any change to `.specify/memory/constitution.md`, any redaction approval,
  any release tag.
- [x] **V. Author/Approver Separation**: PASS. The agent (Claude under
  Claude Code) authors plan and downstream artifacts; the human Source
  ratifies. Self-approval by the agent is excluded by construction.
- [x] **VI. Human Ratification**: PASS. The plan and the substrate it
  defines touch governance, identity, security, and attestation surfaces;
  every transition into `ratified` and every merge of feature 001 is gated
  on Source human ratification per FR-013a, FR-016, FR-017.
- [x] **VII. Verification Over Claims**: PASS. Verification evidence is
  defined as: validator pass on the bundled well-formed examples, validator
  failure on each bundled malformed example, no-LIMITLESS-string scan of
  generic-contract paths, status-lifecycle conformance check, and the
  acceptance scenarios in spec.md US1–US7 walked end-to-end. Self-claims
  without these artifacts MUST NOT be accepted.
- [x] **VIII. Attestation**: PASS (bootstrap clause). The attestation record
  schema is itself an output of this feature, so the plan's own attestation
  is recorded as bootstrap evidence in repository-visible artifacts: the
  spec/plan/tasks triple, commit history, and the validator's pass/fail
  outputs against bundled examples. After this feature ships, future
  Creator-Engine-governed mutations on this substrate MUST emit a v0.1
  attestation record per FR-004 / FR-020a.
- [x] **IX. LIMITLESS as Dogfood**: PASS. LIMITLESS-specific values appear
  only under `tenants/limitless/`. Generic contract documents under
  `docs/contracts/`, `schemas/`, `validators/`, `templates/` contain zero
  LIMITLESS-specific identifiers from the canonical list (FR-024, FR-024a,
  SC-004). The validator enforces this with a reproducible exact-string
  scan.
- [x] **X. Spec Kit Compatibility**: PASS. All Creator Engine fields live in
  adjacent `*.creator-engine.yml` sidecars; Spec Kit `spec.md`, `plan.md`,
  `tasks.md` files remain byte-identical to vanilla Spec Kit. Vanilla Spec
  Kit consumers can read these files unmodified.
- [x] **XI. YAGNI (v0.1)**: PASS. Plan introduces no coordination protocol,
  drift detector, dashboard, hosted policy engine, or multi-tenant SaaS
  behavior. The validator runs locally; no remote enforcement, no live
  source-host API integration, no deploy hooks.
- [x] **XII. Security & Privacy**: PASS. Plan declares the redaction gate as
  policy-and-validation only; v0.1 does not execute any public or NDA-
  visible export workflow. Identity records carry a `signing_policy` field
  but no secret material. Author/approver separation extends to redaction
  approvers (FR-021).

No gate is FAIL. No gate is N/A. Constitution Check passes; Phase 0 may
proceed.

## Project Structure

### Documentation (this feature)

```text
specs/001-v0-1-governance-substrate/
├── plan.md                  # This file (/speckit-plan output)
├── research.md              # Phase 0 output (/speckit-plan output)
├── data-model.md            # Phase 1 output (/speckit-plan output)
├── quickstart.md            # Phase 1 output (/speckit-plan output)
├── contracts/               # Phase 1 output (/speckit-plan output)
│   ├── README.md
│   ├── identity-record.contract.md
│   ├── spec-wrapper-sidecar.contract.md
│   ├── plan-wrapper-sidecar.contract.md
│   ├── tasks-wrapper-sidecar.contract.md
│   ├── mutation-class-taxonomy.contract.md
│   ├── authority-matrix.contract.md
│   ├── ratification-flow.contract.md
│   ├── attestation-record.contract.md
│   ├── ratification-record.contract.md
│   ├── redaction-gate-policy.contract.md
│   ├── redaction-record.contract.md
│   ├── lifecycle-state-machine.contract.md
│   └── validator-cli.contract.md
├── checklists/              # Pre-existing (not output of /speckit-plan)
├── spec.md                  # Pre-existing
└── tasks.md                 # Phase 2 output (/speckit-tasks - NOT created here)
```

### Source Code (repository root)

The substrate's shipped artifacts live in five top-level directories that
correspond directly to FR-022/FR-023/FR-024 path conventions, plus the
substrate's own `specs/` (Spec Kit governed by Creator Engine itself):

```text
docs/
└── contracts/                          # Generic contract documents (LIMITLESS-free, FR-024)
    ├── identity-record.md              # FR-001..FR-005
    ├── spec-wrapper-sidecar.md         # FR-009, FR-012a (governance fields canonical here)
    ├── plan-wrapper-sidecar.md         # FR-012b
    ├── tasks-wrapper-sidecar.md        # FR-012b
    ├── mutation-class-taxonomy.md      # FR-006..FR-008 (baseline + extension rules)
    ├── authority-matrix.md             # FR-015
    ├── ratification-flow.md            # FR-016..FR-018
    ├── attestation-record.md           # FR-004, FR-020a
    ├── ratification-record.md          # FR-016, FR-020a
    ├── redaction-gate-policy.md        # FR-019..FR-021
    ├── redaction-record.md             # FR-020, FR-020a
    ├── lifecycle-state-machine.md      # FR-013, FR-013a, FR-014
    ├── definition-of-ready.md          # FR-013
    ├── definition-of-done.md           # FR-014
    └── verification-spec.md            # FR-030, FR-031 (Creator-Engine-governed itself)

schemas/                                # JSON Schema (Draft 2020-12) files (LIMITLESS-free, FR-024)
├── identity-record.schema.yaml         # FR-001
├── spec-wrapper-sidecar.schema.yaml    # FR-009, FR-012a
├── plan-wrapper-sidecar.schema.yaml    # FR-012b
├── tasks-wrapper-sidecar.schema.yaml   # FR-012b
├── attestation-record.schema.yaml      # FR-004
├── ratification-record.schema.yaml     # FR-016
├── redaction-record.schema.yaml        # FR-020
├── mutation-class.schema.yaml          # FR-006 (baseline + extension rules)
└── authority-matrix.schema.yaml        # FR-015

templates/                              # Project-agnostic templates (LIMITLESS-free, FR-024)
├── identity-record.template.yaml
├── spec.creator-engine.template.yaml
├── plan.creator-engine.template.yaml
├── tasks.creator-engine.template.yaml
├── attestation-record.template.yaml
├── ratification-record.template.yaml
└── redaction-record.template.yaml

validators/                             # Validator implementation (LIMITLESS-free, FR-024)
├── README.md
├── requirements.txt                    # PyYAML, jsonschema
├── wheelhouse/                          # Checked-in offline wheels for pinned runtime deps
├── pyproject.toml
├── creator_engine_validator/
│   ├── __init__.py
│   ├── __main__.py                     # CLI entrypoint (`python -m creator_engine_validator`)
│   ├── cli.py                          # Argument parsing, exit codes
│   ├── loader.py                       # YAML/Markdown loading, sidecar discovery
│   ├── schema.py                       # JSON Schema wrappers per artifact type
│   ├── checks/
│   │   ├── identity.py                 # FR-001 completeness
│   │   ├── sidecar_conformance.py      # FR-009/012a/012b
│   │   ├── mutation_class.py           # FR-006..FR-008 (baseline + class/action match)
│   │   ├── lifecycle.py                # FR-013a transitions and ordering
│   │   ├── definition_of_ready.py      # FR-013
│   │   ├── definition_of_done.py       # FR-014 (incl. attestation linkage)
│   │   ├── duplicate_spec_id.py        # FR-027a
│   │   ├── attestation_linkage.py      # FR-004, FR-020a
│   │   ├── ratification.py             # FR-016..FR-018, FR-007
│   │   ├── redaction_gate.py           # FR-019..FR-021
│   │   └── no_limitless_strings.py     # FR-024, FR-024a, SC-004
│   ├── reporting.py                    # Contract-referenced error messages (FR-027)
│   └── version.py
└── tests/
    ├── unit/
    └── integration/                    # Runs validator against examples/* and tenants/limitless/

examples/                               # Project-agnostic example tenant (FR-028, FR-029)
├── README.md
├── well-formed/
│   ├── identity-record.yml
│   ├── spec.md
│   ├── spec.creator-engine.yml
│   ├── plan.md
│   ├── plan.creator-engine.yml
│   ├── tasks.md
│   ├── tasks.creator-engine.yml
│   ├── attestations/
│   │   └── 2026-05-09-EX-MUT-001.yml
│   ├── ratifications/
│   │   └── 2026-05-09-EX-MUT-001.yml
│   └── redactions/
│       └── 2026-05-09-EX-RED-001.yml
└── malformed/
    ├── identity-record.missing-fields.yml          # FR-001 violation
    ├── spec.creator-engine.missing-acceptance.yml  # FR-013 violation
    ├── tasks.creator-engine.class-action-mismatch.yml  # FR-006/FR-027a
    ├── attestation-record.missing-ratifier.yml     # FR-004 violation
    ├── duplicate-spec-id/                          # FR-027a violation pair
    ├── lifecycle-skipped-state.yml                 # FR-013a violation
    ├── self-ratification.yml                       # FR-007 violation
    └── redaction-record.missing-policy-version.yml # FR-020 violation

tenants/                                # Tenant fixtures (FR-022, FR-023)
└── limitless/                          # LIMITLESS dogfood fixture
    ├── README.md
    ├── identity-record.yml             # zero TBDs (SC-005)
    ├── limitless-identifiers.yml       # canonical non-secret identifier list (FR-024a)
    ├── repositories.yml
    ├── mutation-classes.yml            # baseline + LIMITLESS extension overlay (FR-006)
    ├── authority-matrix-overlay.yml    # tenant overlay rows (FR-015)
    ├── ratification-flow.yml           # LIMITLESS surfaces and roles (FR-016)
    ├── attestations/                   # tenant-declared attestation_storage_path
    ├── ratifications/                  # tenant-declared ratification_storage_path
    └── redactions/                     # tenant-declared redaction_storage_path

specs/                                  # Substrate's own Spec Kit specs (NOT a generic contract path per FR-024)
└── 001-v0-1-governance-substrate/      # This feature

.specify/                               # Spec Kit substrate (pre-existing)
├── memory/constitution.md              # NOT a generic contract path per FR-024
├── templates/                          # Spec Kit templates (distinct from /templates/)
└── scripts/

AGENTS.md                               # Pre-existing
CLAUDE.md                               # Pre-existing (updated by /speckit-plan to point at this plan)
README.md                               # NOT a generic contract path per FR-024
```

**Structure Decision**: The substrate is a single repository with five
shipped top-level artifact directories (`docs/contracts/`, `schemas/`,
`templates/`, `validators/`, `examples/`) plus the LIMITLESS dogfood
fixture at `tenants/limitless/`. The four "generic contract" paths
defined in FR-024 (`docs/contracts/`, `schemas/`, `validators/`,
`templates/`) are the surface that the no-LIMITLESS-strings validator
check and SC-004 apply to. `specs/`, `.specify/memory/constitution.md`,
and `README.md` are substrate-development artifacts and are explicitly
excluded from FR-024 per the spec's clarification. The validator is a
small Python package under `validators/` with a CLI entrypoint and a
checks/ module mapped one-to-one to the functional requirements it
enforces; this keeps each FR auditable to a concrete check function and
keeps error messages directly cite-able to the violated FR (FR-027).

## Complexity Tracking

> No Constitution Check violations require justification. Plan passes all
> twelve gates; no entries.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| —         | —          | —                                    |

## Post-Design Constitution Re-Check

*Re-evaluated after Phase 1 design (research.md, data-model.md, contracts/,
quickstart.md, CLAUDE.md update).*

- [x] **I. Spec-First**: PASS. Phase 1 artifacts are direct outputs of the
  approved spec; no new scope introduced.
- [x] **II. Repo-Native (v0.1)**: PASS. All Phase 1 artifacts are files in
  this repository.
- [x] **III. Explicit Agent Identity**: PASS. Identity remains as recorded
  in the pre-Phase-0 check; Phase 1 artifacts do not introduce new agent
  actors.
- [x] **IV. Mutation-Class Governance**: PASS. Phase 1 artifacts fall under
  the same `governance / identity / schema / attestation / docs` classes
  declared in the pre-Phase-0 check; the data model and contracts make
  these classes machine-checkable.
- [x] **V. Author/Approver Separation**: PASS. Phase 1 design names the
  ratifier-of-this-feature as the human Source, distinct from the agent
  authoring this plan.
- [x] **VI. Human Ratification**: PASS. Phase 1 contracts encode the
  six-state lifecycle's `verified → ratified` transition as the
  enforcement point for human ratification on privileged classes.
- [x] **VII. Verification Over Claims**: PASS. quickstart.md defines the
  exact validator commands, expected outputs, and the malformed-example
  failure modes that constitute verification evidence; no claim is
  accepted without these artifacts.
- [x] **VIII. Attestation**: PASS. Phase 1 contracts define the v0.1
  attestation record format and storage layout; the data model encodes the
  pre-merge / post-merge finalization states.
- [x] **IX. LIMITLESS as Dogfood**: PASS. Phase 1 contracts and schemas are
  authored without LIMITLESS-specific identifiers; LIMITLESS values appear
  only in the `tenants/limitless/` fixture, and the validator enforces this
  via the no-LIMITLESS-strings check.
- [x] **X. Spec Kit Compatibility**: PASS. Phase 1 design carries all
  Creator Engine governance metadata in `*.creator-engine.yml` sidecars;
  vanilla Spec Kit files remain byte-identical.
- [x] **XI. YAGNI (v0.1)**: PASS. Phase 1 introduces no coordination
  protocol, drift detector, dashboard, hosted policy engine, or
  multi-tenant SaaS behavior. The validator is local-only.
- [x] **XII. Security & Privacy**: PASS. Phase 1 contracts define the
  redaction gate as policy-and-validation only; no public/NDA export
  workflow is introduced. Author/approver separation extends to redaction
  approvers in the redaction-record schema.

No gate is FAIL. No gate is N/A. Post-design Constitution Check passes;
Phase 2 (`/speckit-tasks`) may proceed.
