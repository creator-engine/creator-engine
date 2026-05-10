---

description: "Tasks for Creator Engine v0.1 Governance Substrate"
---

# Tasks: Creator Engine v0.1 Governance Substrate

**Input**: Design documents from `/specs/001-v0-1-governance-substrate/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Validator unit and integration tests are explicitly required by
plan.md (Testing section) and FR-025/FR-026/FR-027/SC-006/SC-007. Tests are
INCLUDED in this task list.

**Organization**: Tasks are grouped by user story to enable independent
implementation and testing of each story. Each story is a vertical slice
through the substrate (contract document → schema → template → validator
check → fixtures → tests).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1..US7); Setup/Foundational/Polish carry no story label
- Creator Engine governance metadata for task mutation class, permitted actions, evidence references, and author/approver separation belongs in adjacent `tasks.creator-engine.yml`, not in this vanilla Spec Kit `tasks.md` body.

## Path Conventions

This is a **single-repository governance substrate**. Per plan.md "Project Structure":

- Authored content: `docs/contracts/`, `schemas/`, `templates/`, `examples/`, `tenants/limitless/`
- Validator package: `validators/creator_engine_validator/` with `checks/` submodule
- Validator tests: `validators/tests/unit/`, `validators/tests/integration/`
- Substrate-development artifacts: `specs/`, `.specify/memory/constitution.md`, `README.md` (NOT subject to FR-024)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the substrate's top-level directory layout and the Python validator package skeleton so every later phase has a stable file home.

- [X] T001 Create top-level shipped artifact directories with `.gitkeep` placeholders: `docs/contracts/`, `schemas/`, `templates/`, `examples/well-formed/`, `examples/malformed/`, `tenants/limitless/`
- [X] T002 Create `validators/pyproject.toml` declaring the `creator_engine_validator` package, Python 3.11 requirement, and a `console_scripts` entrypoint per Decision 1 / validator-cli contract
- [X] T003 [P] Pin `PyYAML` and `jsonschema` (Draft 2020-12) versions in `validators/requirements.txt` per Decision 2
- [X] T004 [P] Vendor offline wheels for `PyYAML`, `jsonschema`, and their pure-Python transitive deps into `validators/wheelhouse/` so `pip install --no-index --find-links validators/wheelhouse -r validators/requirements.txt` succeeds offline (FR-026, quickstart.md §Prerequisites)
- [X] T005 [P] Author `validators/README.md` with the offline install + invocation steps from quickstart.md §Prerequisites and §5
- [X] T006 Create the validator package skeleton: `validators/creator_engine_validator/__init__.py`, `__main__.py` invoking `cli.main`, `version.py` with `__version__ = "0.1.0"`, and a stub `cli.py` exposing `main(argv)` returning exit code 2 (invocation error) until subcommands land

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core validator infrastructure (YAML loading, schema engine wrapper, error reporting, check registry, test scaffolding) that every per-story check depends on.

**CRITICAL**: No user story phase may begin until Phase 2 is complete.

- [X] T007 Implement `validators/creator_engine_validator/loader.py` with `load_yaml(path)` using `yaml.safe_load`, sidecar discovery (directory adjacency, canonical names per Decision 4: `spec.creator-engine.yml`, `plan.creator-engine.yml`, `tasks.creator-engine.yml`), and tenant identity-record discovery
- [X] T008 Implement `validators/creator_engine_validator/schema.py` wrapping `jsonschema` Draft 2020-12 with helpers that load YAML-encoded schemas from `schemas/` and produce `ValidationError`s carrying the offending JSON Pointer path
- [X] T009 [P] Implement `validators/creator_engine_validator/reporting.py` with the FR-027 error message contract from `validator-cli.contract.md`: every error cites the violated FR/clause, the specific field or path, and the contract document path
- [X] T010 [P] Set up pytest scaffolding under `validators/tests/` (unit/, integration/, conftest.py with shared fixtures for example/tenant tree paths)
- [X] T011 Implement check registry in `validators/creator_engine_validator/checks/__init__.py` (registry dict mapping check name → callable + FR list) and wire `--list-checks` in `cli.py` per validator-cli contract §Subcommands
- [X] T012 Implement CLI subcommand parsing in `cli.py` for `check`, `check-examples`, `scan-no-limitless`, plus `--json` and `--tenant <name>` flags, with exit codes 0/1/2 per validator-cli contract §Exit codes (subcommand bodies remain stubs returning 0 until per-story checks register)
- [X] T013 [P] Author `docs/contracts/README.md` listing every shipped contract document and the FR each enforces (mirrors plan.md §Project Structure tree)
- [X] T014 [P] Author `examples/README.md` describing the `well-formed/` vs `malformed/` convention, the FR each malformed exemplar violates, and the expected validator behavior per FR-028/FR-029
- [X] T015 [P] Author `tenants/limitless/README.md` declaring the LIMITLESS dogfood fixture, its storage roots, and a pointer to `limitless-identifiers.yml` for the no-LIMITLESS scan

**Checkpoint**: Foundation ready — user story implementation can now begin.

---

## Phase 3: User Story 1 - Tenant Identity & Authority Discoverable from Repo Artifacts (Priority: P1) MVP

**Goal**: A reviewer with `git clone` can read a tenant identity record and name the tenant, source host, agent app slug, agent actor identity, allowed repositories, and signing policy without consulting any external system.

**Independent Test**: Author one example tenant identity record under `examples/well-formed/identity-record.yml`; load it with the validator's `identity.py` check; observe a clean pass and a printed summary of the declared identity. Author one malformed counterpart missing `human_ratifier_roles`; observe a contract-referenced FR-001 error.

**Source FRs**: FR-001, FR-002, FR-003, FR-004 (storage paths only), FR-005

### Contract & schema for User Story 1

- [X] T016 [P] [US1] Author `docs/contracts/identity-record.md` enumerating every field from data-model.md Entity 1 (tenant_id, source_host, source_host_installation_id, agent_app_slug, agent_actor_id, runtime_tool, role_category, authority_context, human_ratifier_roles, mutation_classes, allowed_repositories, signing_policy, attestation/ratification/redaction_storage_path, optional platform_identity_ref) and citing FR-001..FR-005
- [X] T017 [P] [US1] Author `schemas/identity-record.schema.yaml` (JSON Schema Draft 2020-12 in YAML) encoding all required/optional fields and constraints from Entity 1, with `unevaluatedProperties: false`
- [X] T018 [P] [US1] Author `templates/identity-record.template.yaml` as a project-agnostic, fully-commented identity-record skeleton tenants copy from (zero LIMITLESS strings per FR-024)

### Validator check for User Story 1

- [X] T019 [US1] Implement `validators/creator_engine_validator/checks/identity.py` performing schema validation against `schemas/identity-record.schema.yaml`, asserting `human_ratifier_roles` is non-empty per spec edge case, asserting `attestation/ratification/redaction_storage_path` directories exist or are tolerated empty per data-model.md, and emitting FR-001 / FR-005 citations on failure (depends on T008, T009, T011)
- [X] T020 [US1] Register `identity` check in the registry (`__init__.py`) so `--list-checks` advertises FR-001..FR-005 (depends on T011, T019)

### Fixtures for User Story 1

- [X] T021 [P] [US1] Author `examples/well-formed/identity-record.yml` — a project-agnostic well-formed identity record (FR-028) using the example-tenant naming from data-model.md
- [X] T022 [P] [US1] Author `examples/malformed/identity-record.missing-fields.yml` deliberately omitting required fields (e.g. empty `human_ratifier_roles`) to demonstrate FR-001 failure per FR-029

### Tests for User Story 1

- [X] T023 [P] [US1] Unit-test `identity.py` against an in-memory well-formed dict and several malformed dicts (missing each required field; empty `human_ratifier_roles`); assert error citations include `FR-001` and `docs/contracts/identity-record.md`
- [X] T024 [US1] Integration test in `validators/tests/integration/test_identity_examples.py` invoking the CLI against the well-formed and malformed identity examples; assert exit code 0 / 1 respectively and that the failure message cites `FR-001`

**Checkpoint**: US1 fully functional. A reviewer can read the example identity record, run `python -m creator_engine_validator check examples/well-formed/identity-record.yml`, see a pass, and run the malformed counterpart to see an FR-001 failure.

---

## Phase 4: User Story 2 - Versioned Spec Format Defines Work and Acceptance (Priority: P1)

**Goal**: A tenant can author Spec Kit `spec.md` plus a `spec.creator-engine.yml` sidecar (and adjacent plan/tasks sidecars) and have the validator confirm wrapper conformance, type taxonomy membership, scope/acceptance/verification presence, and known status — while Spec Kit Markdown files remain byte-identical to vanilla Spec Kit.

**Independent Test**: Author one well-formed `spec.md` + `spec.creator-engine.yml` pair plus a `plan.md` + sidecar plus a `tasks.md` + sidecar under `examples/well-formed/`; observe a clean validator pass. Author one sidecar missing `acceptance_criteria` and one with a duplicate `id`; observe FR-013 and FR-027a failures with the specific field named.

**Source FRs**: FR-009, FR-010, FR-011, FR-012, FR-012a, FR-012b, FR-013 (DoR field-presence subset)

### Contracts & schemas for User Story 2

- [X] T025 [P] [US2] Author `docs/contracts/spec-wrapper-sidecar.md` enumerating Entity 3 fields, the FR-009 compatibility-vs-canonical rule, the seven-value `spec_type` taxonomy from FR-011, and the FR-012a sidecar discovery rule
- [X] T026 [P] [US2] Author `docs/contracts/plan-wrapper-sidecar.md` enumerating Entity 4 fields and citing FR-012a/FR-012b
- [X] T027 [P] [US2] Author `docs/contracts/tasks-wrapper-sidecar.md` enumerating Entity 5 (TaskEntry sub-object) and citing FR-012a/FR-012b
- [X] T028 [P] [US2] Author `docs/contracts/definition-of-ready.md` declaring scope/acceptance_criteria/verification non-empty as the `draft → ready` gate per FR-013
- [X] T029 [P] [US2] Author `schemas/spec-wrapper-sidecar.schema.yaml` encoding Entity 3 (status enum locked to the six FR-013a values; `spec_type` enum locked to FR-011 values; verification.method/evidence_refs structure)
- [X] T030 [P] [US2] Author `schemas/plan-wrapper-sidecar.schema.yaml` encoding Entity 4
- [X] T031 [P] [US2] Author `schemas/tasks-wrapper-sidecar.schema.yaml` encoding Entity 5 with the per-TaskEntry constraint that `approver_actor_id != author_actor_id`
- [X] T032 [P] [US2] Author `templates/spec.creator-engine.template.yaml` (LIMITLESS-free)
- [X] T033 [P] [US2] Author `templates/plan.creator-engine.template.yaml` (LIMITLESS-free)
- [X] T034 [P] [US2] Author `templates/tasks.creator-engine.template.yaml` (LIMITLESS-free)

### Validator checks for User Story 2

- [X] T035 [US2] Implement `sidecar_conformance.py` performing schema validation against the three wrapper-sidecar schemas; emits FR-009 / FR-012a / FR-012b citations; also enforces the FR-009 compatibility-vs-canonical rule when a Spec Kit Markdown file carries a frontmatter title that disagrees with the sidecar value (warning or failure per the schema rule, never silent override)
- [X] T036 [P] [US2] Implement `duplicate_spec_id.py` walking every `spec.creator-engine.yml` discoverable from the target paths and reporting any duplicate `id` value with FR-027a citation
- [X] T037 [P] [US2] Implement `definition_of_ready.py` asserting that for any spec sidecar at `status` ≥ `ready`, `scope`, `acceptance_criteria`, and `verification` are non-empty per FR-013
- [X] T038 [US2] Register `sidecar_conformance`, `duplicate_spec_id`, and `definition_of_ready` checks in the registry advertising FR-009/012a/012b/013/027a (depends on T011, T035, T036, T037)

### Fixtures for User Story 2

- [X] T039 [P] [US2] Author `examples/well-formed/spec.md` as a vanilla Spec Kit Markdown file (no Creator Engine fields in body or frontmatter, FR-010, US2 AS4)
- [X] T040 [P] [US2] Author `examples/well-formed/spec.creator-engine.yml` with all required fields populated (status `ready` so DoR fires)
- [X] T041 [P] [US2] Author `examples/well-formed/plan.md` (vanilla) and `examples/well-formed/plan.creator-engine.yml` (well-formed sidecar referencing the spec)
- [X] T042 [P] [US2] Author `examples/well-formed/tasks.md` (vanilla) and `examples/well-formed/tasks.creator-engine.yml` with per-task entries (mutation_class, permitted_actions, verification_evidence_ref, distinct author/approver actor ids)
- [X] T043 [P] [US2] Author the FR-013 violation fixture omitting `acceptance_criteria`
- [X] T044 [P] [US2] Author the FR-027a duplicate-id pair under `examples/malformed/duplicate-spec-id/` (two sidecars sharing the same `id`)

### Tests for User Story 2

- [X] T045 [P] [US2] Unit tests for the three checks against in-memory well-formed and malformed dicts; assert error citations include `FR-009`/`FR-012a`/`FR-013`/`FR-027a` plus contract document paths
- [X] T046 [US2] Integration test invoking the CLI against `examples/well-formed/` (pass) and each `examples/malformed/spec.creator-engine.*.yml` and the `duplicate-spec-id/` directory (fail with the expected FR citation)

**Checkpoint**: US2 fully functional. The well-formed example pair validates; each malformed counterpart fails with a contract-referenced error.

---

## Phase 5: User Story 3 - Ratifier Identifiable per Mutation Class (Priority: P1)

**Goal**: A reviewer reading the authority matrix and ratification flow can pick any baseline mutation class and state the required ratifier role, the valid ratification surfaces, the required audit artifacts, and that the implementer is barred from self-ratifying.

**Independent Test**: Walk three baseline classes (`docs`, `deploy`, `governance`) through the matrix and observe three distinct ratifier outcomes; confirm `deploy` and `governance` require human ratifier per FR-008. Run the validator against a malformed `tasks.creator-engine.yml` whose task declares an action outside its declared class's vocabulary and observe an FR-006/FR-027a class/action mismatch error. Run against a fixture where author == ratifier and observe FR-007.

**Source FRs**: FR-006, FR-007, FR-008, FR-015, FR-016, FR-017, FR-018, FR-027a (class/action mismatch)

### Contracts & schemas for User Story 3

- [ ] T047 [P] [US3] Author `docs/contracts/mutation-class-taxonomy.md` declaring the nine baseline classes (`docs`, `code`, `schema`, `deploy`, `governance`, `identity`, `security`, `attestation`, `redaction`), the reserved-action vocabulary from data-model.md Entity 2, the FR-008 privileged-class human-ratifier rule, and the tenant-extension overlay rule per Decision 8
- [ ] T048 [P] [US3] Author `docs/contracts/authority-matrix.md` with concrete baseline rows for every baseline class × generic role category (FR-015), each row populating allowed_instruction_sources / allowed_mutation_classes / required_ratifier_role / allowed_communication_surfaces / required_audit_artifacts (zero LIMITLESS-specific values)
- [ ] T049 [P] [US3] Author `docs/contracts/ratification-flow.md` with the generic flow rules per Entity 7, FR-016, FR-017 (agent text NOT ratification for FR-008 classes), and FR-018 ("go ahead" not merge authorization)
- [ ] T050 [P] [US3] Author `schemas/mutation-class.schema.yaml` encoding Entity 2 (name kebab-case; is_baseline; action_vocabulary drawn from reserved set; agent_permitted_actions ⊆ action_vocabulary; FR-008 privileged-class rule excluding merge/deploy/publish/credential/settings/redaction-approval/gate-weakening from agent_permitted_actions)
- [ ] T051 [P] [US3] Author `schemas/authority-matrix.schema.yaml` encoding Entity 6 row shape (role_category enum; tenant_role_name optional; allowed_* and required_* fields per data-model.md)

### Validator checks for User Story 3

- [ ] T052 [US3] Implement `mutation_class.py` performing: baseline-class presence (substrate ships all nine; tenants MUST NOT remove); tenant-extension classes MUST NOT reuse baseline names; every action ∈ reserved vocabulary; agent_permitted_actions ⊆ action_vocabulary; FR-008 privileged-class action exclusion; class/action mismatch detection across spec/plan/tasks sidecars per FR-027a
- [ ] T053 [P] [US3] Implement `ratification.py` performing: ratification-record existence for any spec at `ratified` or `done`; surface validity against the ratification-flow's `valid_ratification_surfaces`; ratifier ≠ author per FR-007 (cross-checks `tasks.creator-engine.yml` author/approver fields); agent-authored review text NOT ratification for FR-008 classes (FR-017); "go ahead" not on a designated surface NOT ratification (FR-018)
- [ ] T054 [US3] Register `mutation_class` and `ratification` checks advertising FR-006..FR-008/FR-015..FR-018/FR-027a (depends on T011, T052, T053)

### Fixtures for User Story 3

- [ ] T055 [P] [US3] Author the FR-006/FR-027a class/action mismatch fixture (e.g. a `docs`-class task declaring `merge` or `deploy` action)
- [ ] T056 [P] [US3] Author the FR-007 self-ratification fixture (ratification record whose `ratifier_actor_id` equals the spec/tasks `author_actor_id`)

### Tests for User Story 3

- [ ] T057 [P] [US3] Unit-test `mutation_class.py` against: baseline taxonomy parse, missing baseline class, tenant extension reusing a baseline name, action outside reserved vocab, agent_permitted_actions exceeding action_vocabulary, FR-008 privileged-class agent action violation, and a class/action mismatch in a tasks sidecar
- [ ] T058 [P] [US3] Unit-test `ratification.py` against: missing ratification record for `ratified` spec, surface not in `valid_ratification_surfaces`, ratifier == author, and agent-authored ratification of an FR-008 class
- [ ] T059 [US3] Integration test invoking the CLI against `examples/malformed/tasks.creator-engine.class-action-mismatch.yml` (FR-006/027a) and `examples/malformed/self-ratification.yml` (FR-007)

**Checkpoint**: US3 fully functional. A reviewer can answer "who ratifies this class?" from `docs/contracts/authority-matrix.md` alone, and the validator catches both class/action mismatches and self-ratification.

---

## Phase 6: User Story 4 - Verification Evidence and Attestation Record (Priority: P2)

**Goal**: A reviewer can read any merged mutation's attestation record and read off spec, agent identity, mutation class, permitted-actions list, verification evidence, and ratifier — entirely from repository content. The lifecycle (`draft → ready → in_progress → verified → ratified → done`) is enforced with no skipped transitions.

**Independent Test**: Walk one well-formed mutation through the lifecycle by reading `examples/well-formed/`'s `spec.creator-engine.yml`, `tasks.creator-engine.yml`, attestation record (`pre_merge` / `finalized`), and ratification record. Run the validator against malformed counterparts: missing-ratifier attestation (FR-004), skipped-state lifecycle (FR-013a), and a `done` spec lacking a `finalized` attestation (FR-014/FR-013a).

**Source FRs**: FR-004, FR-005, FR-013a, FR-014, FR-016, FR-020a (storage layout)

### Contracts & schemas for User Story 4

- [ ] T060 [P] [US4] Author `docs/contracts/lifecycle-state-machine.md` enumerating the six states, the gate per transition, the forbidden-transition list, and citing FR-013a
- [ ] T061 [P] [US4] Author `docs/contracts/definition-of-done.md` declaring required evidence (`method` and `evidence_refs[]`), the self-claim rejection rule, and the FR-014 attestation-linkage requirement that no spec enters `done` without an FR-004 attestation
- [ ] T062 [P] [US4] Author `docs/contracts/attestation-record.md` enumerating Entity 8 fields, the `pre_merge`/`finalized` discriminator (Decision 13), the FR-020a filename convention, and the FR-007 author≠ratifier rule
- [ ] T063 [P] [US4] Author `docs/contracts/ratification-record.md` enumerating Entity 9 fields and the FR-020a filename convention
- [ ] T064 [P] [US4] Author `schemas/attestation-record.schema.yaml` encoding Entity 8 with `oneOf` to enforce `state == finalized` ⇒ `merge_reference` populated; `state == pre_merge` ⇒ `merge_reference` absent
- [ ] T065 [P] [US4] Author `schemas/ratification-record.schema.yaml` encoding Entity 9
- [ ] T066 [P] [US4] Author `templates/attestation-record.template.yaml` (LIMITLESS-free)
- [ ] T067 [P] [US4] Author `templates/ratification-record.template.yaml` (LIMITLESS-free)

### Validator checks for User Story 4

- [ ] T068 [P] [US4] Implement `lifecycle.py` deriving the historical sequence of `status` values from `git log` on each `spec.creator-engine.yml` per Decision 7; confirm each transition is gated as data-model.md §State Transitions describes; emit FR-013a citations for any skip or backflow
- [ ] T069 [P] [US4] Implement `definition_of_done.py` rejecting self-claims (a spec at `verified` whose only evidence ref is authored by the same agent identity is rejected per FR-014) and asserting that `done` requires a `finalized` attestation per FR-013a/FR-014
- [ ] T070 [P] [US4] Implement `attestation_linkage.py` asserting: every `verified` spec has a matching `pre_merge` attestation under the tenant's `attestation_storage_path`; every `done` spec has a matching `finalized` attestation with `merge_reference`; the attestation's `mutation_class` matches the spec's; the `ratifier_identity_ref` is distinct from the author
- [ ] T071 [US4] Register `lifecycle`, `definition_of_done`, `attestation_linkage` advertising FR-004/FR-013a/FR-014/FR-020a (depends on T011, T068, T069, T070)

### Fixtures for User Story 4

- [ ] T072 [P] [US4] Author the well-formed attestation record (state can be `finalized` so the well-formed spec at `done` validates; quickstart §4)
- [ ] T073 [P] [US4] Author the well-formed ratification record matching the attestation's `mutation_id`
- [ ] T074 [P] [US4] Author the FR-004 missing-ratifier attestation fixture
- [ ] T075 [P] [US4] Author a `spec.creator-engine.yml` declaring `status: verified` without prior `ready`/`in_progress` history (FR-013a)

### Tests for User Story 4

- [ ] T076 [P] [US4] Unit-test `lifecycle.py` against synthetic git-log traces (skip, backflow, valid) — use a fixture-mock for git log so tests stay offline
- [ ] T077 [P] [US4] Unit-test `attestation_linkage.py` against pre_merge/finalized matchups, missing pre_merge for verified spec, missing finalized for done spec, mutation_class mismatch, and ratifier == author
- [ ] T078 [P] [US4] Unit-test `definition_of_done.py` against self-claim rejection and missing-attestation-for-done rejection
- [ ] T079 [US4] Integration test invoking the CLI against the well-formed example (pass through lifecycle to `done`) and against `attestation-record.missing-ratifier.yml` (FR-004) and `lifecycle-skipped-state.yml` (FR-013a)

**Checkpoint**: US4 fully functional. The lifecycle is enforceable end-to-end; attestation and ratification records bind a mutation to identity, spec, class, evidence, and ratifier.

---

## Phase 7: User Story 5 - Redaction Gate Policy for Future Public or NDA-Visible Export (Priority: P2)

**Goal**: A tenant artifact declaring future public or NDA-visible export intent is treated as ineligible unless a redaction record exists that names source artifact, redacted regions, approver, and policy version. v0.1 implements the policy and validation; no export workflow is executed.

**Independent Test**: Validate one fixture declaring `export_intent: public` without a redaction record and observe a contract-referenced FR-019/FR-020 failure. Validate one well-formed redaction record and observe a clean pass. Validate a fixture where the redaction approver equals the source artifact's author and observe FR-021.

**Source FRs**: FR-019, FR-020, FR-020a, FR-021

### Contracts & schemas for User Story 5

- [ ] T080 [P] [US5] Author `docs/contracts/redaction-gate-policy.md` enumerating Entity 10 fields, the public/NDA-visible export-intent enum, and the v0.1-policy-only scope (no export workflow executed)
- [ ] T081 [P] [US5] Author `docs/contracts/redaction-record.md` enumerating Entity 11 fields and the FR-020a filename convention
- [ ] T082 [P] [US5] Author `schemas/redaction-record.schema.yaml` encoding Entity 11
- [ ] T083 [P] [US5] Author `templates/redaction-record.template.yaml` (LIMITLESS-free)

### Validator check for User Story 5

- [ ] T084 [US5] Implement `redaction_gate.py` asserting: any artifact declaring `export_intent: public` or `export_intent: nda_visible` references a Redaction Record bound to a known `policy_version`; the redaction approver ≠ source artifact author per FR-021
- [ ] T085 [US5] Register `redaction_gate` advertising FR-019..FR-021 (depends on T011, T084)

### Fixtures for User Story 5

- [ ] T086 [P] [US5] Author the well-formed redaction record fixture
- [ ] T087 [P] [US5] Author the FR-020 missing-policy-version fixture

### Tests for User Story 5

- [ ] T088 [P] [US5] Unit-test `redaction_gate.py` against: `export_intent` declared but no redaction record (FR-019), redaction record missing `policy_version` (FR-020), and approver == author (FR-021)
- [ ] T089 [US5] Integration test invoking the CLI against the well-formed redaction record (pass) and `redaction-record.missing-policy-version.yml` (FR-020 failure)

**Checkpoint**: US5 fully functional. A reviewer can confirm that any export-declaring artifact is gated by a redaction record bound to a policy version with author/approver separation.

---

## Phase 8: User Story 6 - LIMITLESS Dogfood Tenant Mapping (Priority: P3)

**Goal**: The substrate ships a populated LIMITLESS tenant fixture that maps the current LIMITLESS fleet onto the generic v0.1 contracts with zero unresolved fields and zero LIMITLESS-specific identifiers in the four generic-contract paths.

**Independent Test**: Read `tenants/limitless/` end to end; confirm zero `TBD`/deferred fields per SC-005. Run `python -m creator_engine_validator scan-no-limitless` and observe `0 matches` per SC-004. Run `python -m creator_engine_validator check tenants/limitless/` and observe a clean pass.

**Source FRs**: FR-022, FR-023, FR-024, FR-024a

### LIMITLESS dogfood fixture files

- [ ] T090 [P] [US6] Author `tenants/limitless/limitless-identifiers.yml` — the canonical, non-secret identifier list (host names, channel names, bot slugs, bot actor ids, repository names) used by `no_limitless_strings.py` per FR-024a
- [ ] T091 [P] [US6] Author `tenants/limitless/identity-record.yml` populated with concrete LIMITLESS values (`tenant_id: limitless`, `agent_app_slug: limitless-agent[bot]`, etc.); zero TBDs per SC-005
- [ ] T092 [P] [US6] Author `tenants/limitless/repositories.yml` listing the LIMITLESS allowed repositories declared by the identity record
- [ ] T093 [P] [US6] Author `tenants/limitless/mutation-classes.yml` carrying the baseline + LIMITLESS extension classes (each extension `is_baseline: false`, drawing actions from the reserved vocabulary; baseline names not redefined)
- [ ] T094 [P] [US6] Author `tenants/limitless/authority-matrix-overlay.yml` carrying tenant-specific role names in the `tenant_role_name` field (FR-015 tenant-fixture rule)
- [ ] T095 [P] [US6] Author `tenants/limitless/ratification-flow.yml` naming LIMITLESS surfaces and roles per Entity 7
- [ ] T096 [P] [US6] Create the three LIMITLESS storage roots (`attestations/`, `ratifications/`, `redactions/`) with `.gitkeep` so the validator can resolve `attestation_storage_path` etc. per data-model.md

### No-LIMITLESS validator check

- [ ] T097 [US6] Implement `no_limitless_strings.py` loading `tenants/limitless/limitless-identifiers.yml` and performing exact-substring search across every file under the four generic-contract paths (`docs/contracts/`, `schemas/`, `validators/`, `templates/`); emits FR-024/FR-024a citations naming the matched identifier and offending file path
- [ ] T098 [US6] Register `no_limitless_strings` and wire `scan-no-limitless` subcommand to invoke only that check (depends on T011, T012, T097)

### Tests for User Story 6

- [ ] T099 [P] [US6] Unit-test `no_limitless_strings.py` against synthetic generic-contract path trees (clean tree → 0 matches; tree with a leaked identifier → match reported with file path and identifier)
- [ ] T100 [US6] Integration test invoking `python -m creator_engine_validator check tenants/limitless/` (clean pass; SC-005), `python -m creator_engine_validator scan-no-limitless` (0 matches; SC-004), and asserting no field in the LIMITLESS fixture has the literal string `TBD` (SC-005)

**Checkpoint**: US6 fully functional. The LIMITLESS dogfood fixture validates clean; the no-LIMITLESS scan reports zero matches across the generic-contract paths.

---

## Phase 9: User Story 7 - Machine-Checkable Validation for the Substrate Contracts (Priority: P3)

**Goal**: A reviewer with a fresh `git clone` and no network can run the validator against the bundled examples and observe well-formed pass / malformed fail with FR-cited errors, in under 60 seconds.

**Independent Test**: From a fresh clone, run `python -m venv .venv && source .venv/bin/activate && pip install --no-index --find-links validators/wheelhouse -r validators/requirements.txt && python -m creator_engine_validator check-examples`. Observe exit code 0 and a per-malformed-fixture FR citation table. Wall-clock under 60 seconds.

**Source FRs**: FR-025, FR-026, FR-027, FR-027a, FR-028, FR-029, FR-030, FR-031

### Contracts & verification spec

- [ ] T101 [P] [US7] Author `docs/contracts/validator-cli.md` mirroring the per-feature `validator-cli.contract.md` from `specs/.../contracts/`: subcommands, flags, exit codes, required checks, FR-027 error contract
- [ ] T102 [P] [US7] Author the governed verification spec source `docs/contracts/verification-spec/spec.md` (vanilla Spec Kit Markdown) describing how v0.1 completion itself is verified per FR-030 (the auditor's checks for each of the five governance questions)
- [ ] T103 [P] [US7] Author the canonical sidecar `docs/contracts/verification-spec/spec.creator-engine.yml` (Decision 14) so the verification spec is itself a Creator-Engine-governed artifact per FR-031
- [ ] T104 [P] [US7] Render the human-readable contract document `docs/contracts/verification-spec.md` from the governed source per Decision 14

### CLI integration: `check-examples` subcommand body

- [ ] T105 [US7] Implement the `check-examples` subcommand body: run `check` against `examples/well-formed/` (must pass) and `examples/malformed/` (every fixture must fail with the expected FR citation); exit 0 only when both expectations are met per validator-cli contract §Subcommands and FR-028/FR-029/SC-006 (depends on T012 and every checks/* registered through T020/T038/T054/T071/T085/T098)

### Integration tests covering all stories

- [ ] T106 [P] [US7] Integration test invoking `python -m creator_engine_validator check-examples` from a temp working directory; assert exit 0 and that stdout names every malformed fixture's expected FR (`FR-001`, `FR-013`, `FR-013a`, `FR-007`, `FR-006`/`FR-027a`, `FR-020`, etc.) per quickstart §5
- [ ] T107 [P] [US7] Integration test asserting the validator makes zero network calls (monkey-patch `socket.socket` to raise) during `check-examples` and `scan-no-limitless` per FR-026
- [ ] T108 [P] [US7] Integration test asserting `check-examples` completes in under 60 wall-clock seconds on the bundled examples per SC-007 (with a margin of safety; skip the assertion when the test environment marks itself as constrained)
- [ ] T109 [US7] Integration test asserting `--list-checks` prints exactly the eleven checks named in `validator-cli.contract.md` §Required checks, each with its FR list, per FR-027

**Checkpoint**: US7 fully functional. A fresh-clone reviewer can complete quickstart §5 end-to-end with no network.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Cross-story documentation, the substrate's own self-governance bundle (this feature's spec/plan/tasks sidecars + attestation), and the end-to-end quickstart walkthrough that constitutes v0.1 acceptance evidence.

- [ ] T110 [P] Update top-level `README.md` to point at `docs/contracts/`, the validator quickstart, and `tenants/limitless/`; do NOT introduce LIMITLESS-specific identifiers under any path subject to FR-024 (README.md itself is not subject per the FR-024 clarification)
- [ ] T111 [P] Update `CLAUDE.md` so the "current plan" pointer remains accurate after tasks generation; preserve byte-identical Spec Kit semantics elsewhere
- [ ] T112 [P] Author this feature's own `spec.creator-engine.yml` sidecar (status `ready` initially; will progress through the lifecycle as this feature is implemented and ratified)
- [ ] T113 [P] Author this feature's `plan.creator-engine.yml` per FR-012b
- [ ] T114 [P] Author this feature's `tasks.creator-engine.yml` declaring per-task `mutation_class`, `permitted_actions`, `verification_evidence_ref`, distinct `author_actor_id` / `approver_actor_id`
- [ ] T115 Run quickstart.md §1–§9 end-to-end on a fresh worktree; capture validator output and confirm SC-001, SC-003, SC-004, SC-005, SC-006, SC-007, SC-008, SC-009 by direct artifact inspection (depends on every prior phase)
- [ ] T116 Author the substrate's own bootstrap attestation record under `tenants/limitless/attestations/` per FR-004 / FR-020a, naming the spec, the agent identity, the mutation class set declared in the plan's Constitution Check, the permitted actions, the verification evidence (T115 output), and the ratifier — pre_merge state until merge, finalized after with the merge reference (constitution principle VIII bootstrap clause)
- [ ] T117 Author the matching ratification record once the human Source ratifies the feature per FR-016/FR-017; ratifier MUST be human and MUST NOT equal the agent author per FR-007

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup, T001–T006)**: No dependencies. T002 must precede T006; T003 and T004 can run alongside T002.
- **Phase 2 (Foundational, T007–T015)**: Depends on Phase 1. T007 and T008 must complete before any check (T019, T035, T036, T037, T052, T053, T068, T069, T070, T084, T097). T011 must complete before any check registration (T020, T038, T054, T071, T085, T098). BLOCKS Phase 3+.
- **Phase 3 (US1, T016–T024)**: Depends on Phase 2. Independent of US2/US3/US4/US5.
- **Phase 4 (US2, T025–T046)**: Depends on Phase 2. Independent of US1/US3 modulo shared schema patterns.
- **Phase 5 (US3, T047–T059)**: Depends on Phase 2. References baseline-class names that US4 also uses; classes are declared here, consumed by US4's attestation linkage.
- **Phase 6 (US4, T060–T079)**: Depends on Phase 2 + US2 (status enum + sidecar conformance) + US3 (mutation-class taxonomy + ratification check) for full integration.
- **Phase 7 (US5, T080–T089)**: Depends on Phase 2. Independent of US1/US2/US3/US4 except for sharing Entity 12's verification-evidence shape.
- **Phase 8 (US6, T090–T100)**: Depends on Phase 2 + US1 (identity schema) + US3 (mutation-class & authority schemas) + US4 (storage-root semantics) + US5 (redaction storage root) — LIMITLESS validates against every contract.
- **Phase 9 (US7, T101–T109)**: Depends on every prior phase: `check-examples` runs every check, and the verification spec describes how the substrate verifies itself end-to-end.
- **Phase 10 (Polish, T110–T117)**: Depends on every prior phase. T115 (quickstart walk) blocks T116/T117 because attestation requires the verification evidence the walk produces.

### User Story Dependencies (for parallel staffing)

- **US1, US2, US3, US5** (P1/P1/P1/P2): Can be staffed in parallel after Phase 2 completes; each touches a distinct contract surface and a distinct set of validator checks.
- **US4** (P2): Best staffed after US2 + US3 because attestation linkage references spec-sidecar shape and mutation-class declarations, but its contract documents/schemas/templates can be authored in parallel with those stories.
- **US6** (P3): Should be staffed last among the contract-and-fixture stories because the LIMITLESS fixture validates against every other story's schema.
- **US7** (P3): Staffed last; `check-examples` ties every prior story's check together, and the verification spec narrates the whole substrate.

### Within Each User Story

- Schemas (e.g. T017, T029, T050, T064, T082) MUST exist before checks that consume them (e.g. T019, T035, T052, T068/T070, T084).
- Contract documents (e.g. T016, T025, T047, T060, T080) MUST exist before fixtures that cite them in headers/comments and before checks emit them as `consult` paths in error messages.
- Fixtures (e.g. T021, T039, T055, T072, T086) MUST exist before integration tests that exercise them (T024, T046, T059, T079, T089).
- Unit tests precede integration tests within a story (e.g. T023 before T024, T045 before T046).

### Parallel Opportunities

- All Phase 1 [P] tasks (T003, T004, T005) can run in parallel with each other.
- All Phase 2 [P] tasks (T009, T010, T013, T014, T015) can run in parallel.
- All US1 contract/schema/template authoring [P] tasks (T016, T017, T018) can run in parallel.
- All US2 contract/schema/template authoring [P] tasks (T025–T034) can run in parallel — ten parallel author tasks.
- All US3 contract/schema [P] tasks (T047–T051) can run in parallel.
- All US4 contract/schema/template [P] tasks (T060–T067) can run in parallel.
- All US5 contract/schema/template [P] tasks (T080–T083) can run in parallel.
- All US6 fixture [P] tasks (T090–T096) can run in parallel.
- All US7 contract/spec [P] tasks (T101–T104) can run in parallel.
- Per-story unit tests [P] (T023, T045, T057/T058, T076–T078, T088, T099, T106–T108) can run in parallel within their story.

---

## Parallel Example: User Story 2

```bash
# Author US2 contracts and schemas in parallel:
Task: "Author docs/contracts/spec-wrapper-sidecar.md"           # T025
Task: "Author docs/contracts/plan-wrapper-sidecar.md"           # T026
Task: "Author docs/contracts/tasks-wrapper-sidecar.md"          # T027
Task: "Author docs/contracts/definition-of-ready.md"            # T028
Task: "Author schemas/spec-wrapper-sidecar.schema.yaml"         # T029
Task: "Author schemas/plan-wrapper-sidecar.schema.yaml"         # T030
Task: "Author schemas/tasks-wrapper-sidecar.schema.yaml"        # T031
Task: "Author templates/spec.creator-engine.template.yaml"      # T032
Task: "Author templates/plan.creator-engine.template.yaml"      # T033
Task: "Author templates/tasks.creator-engine.template.yaml"     # T034

# Then sequentially: T035 (sidecar_conformance) — depends on T029/T030/T031.
# Then in parallel: T036 (duplicate_spec_id) and T037 (definition_of_ready).
# Then T038 register, T039–T044 fixtures in parallel, then T045 unit, T046 integration.
```

---

## Implementation Strategy

### MVP (US1 + US2 + US3 + Polish minimum)

1. Complete Phase 1 (Setup) and Phase 2 (Foundational).
2. Complete Phase 3 (US1: Identity).
3. Complete Phase 4 (US2: Spec wrapper).
4. Complete Phase 5 (US3: Mutation class + Ratification).
5. Run quickstart.md §1–§3 end-to-end. Three of the five governance questions are now answerable.
6. **STOP and VALIDATE**: identity, spec format, ratifier are independently demonstrable.

### Incremental Delivery to v0.1 Acceptance

7. Complete Phase 6 (US4: Verification + Attestation). All five governance questions answerable. SC-008 demonstrable.
8. Complete Phase 7 (US5: Redaction Gate). SC-009 demonstrable.
9. Complete Phase 8 (US6: LIMITLESS Dogfood). SC-004, SC-005 demonstrable.
10. Complete Phase 9 (US7: Validator integration + verification spec). SC-006, SC-007 demonstrable.
11. Complete Phase 10 (Polish, self-governance bundle, attestation/ratification of this feature). v0.1 acceptance.

### Parallel Team Strategy

After Phase 2 completes, three engineers can work in parallel:

- Engineer A: US1 (Phase 3) → US4 (Phase 6) — identity → attestation lifecycle thread.
- Engineer B: US2 (Phase 4) → US7 contract docs (T101–T104) — spec format → verification spec thread.
- Engineer C: US3 (Phase 5) → US5 (Phase 7) → US6 (Phase 8) — governance + redaction + dogfood thread.

US7 CLI integration (T105) and integration tests (T106–T109) require all checks to exist; one engineer takes the integration handoff after the others land their checks.

---

## Validation Notes

- Every task above starts with `- [ ]`, has a sequential `T###` id, names a concrete file path, and (where applicable) carries a `[US#]` story label. Creator Engine governance metadata for each task is intentionally excluded from `tasks.md` and belongs in `tasks.creator-engine.yml` per FR-012b.
- No task crosses the byte-identical-Spec-Kit boundary (FR-010, principle X): every Creator Engine governance field lands in a `*.creator-engine.yml` sidecar, never in `spec.md`/`plan.md`/`tasks.md` body or frontmatter.
- No task introduces a LIMITLESS-specific identifier under `docs/contracts/`, `schemas/`, `validators/`, or `templates/` (FR-024); LIMITLESS values appear only under `tenants/limitless/`.
- The validator emerges check-by-check across phases; `--list-checks` advertises the registered checks at any point in the build, so partial implementations are still auditable per FR-027.

---

## Notes

- Tests are explicitly required by plan.md §Testing and FR-025/FR-026/FR-027/SC-006/SC-007; unit tests live under `validators/tests/unit/`, integration tests under `validators/tests/integration/`.
- [P] tasks operate on disjoint files and can be staffed in parallel.
- Verify each unit test fails before its check is implemented; commit after each task or logical group; stop at any checkpoint to validate the story independently.
- Avoid: vague tasks, same-file conflicts, cross-story dependencies that break the independent-test property.
