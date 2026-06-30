# Governance Specification: Retire Spec-Kit — Amend Constitution Principle X

**Feature Branch**: `ce-speckit-retire-principle-x`
**Created**: 2026-06-30
**Status**: Ratified
**Mutation class**: governance
**Source (Operator) approval**: Ratified 2026-06-30 — spec-kit full retirement;
Principle X (Spec Kit Compatibility) replaced by Principle X (CE-Native Spec
Substrate).

## Decision

Creator Engine's own cev3 Scope lifecycle (Frame → Shape → Build → Review →
Ship) is the first-class, native feature-spec substrate. The vendored spec-kit
tool and its associated Claude-Code skill layer are retired. The spec.md /
plan.md / tasks.md plain-Markdown artifact format remains the canonical wire
format; CE governs these artifacts natively without spec-kit tooling.

The current constitution Principle X ("Spec Kit Compatibility") mandates that
Creator Engine MUST NOT break Spec-Kit-only workflows. This mandate is no
longer correct: CE has its own governed lifecycle substrate and retaining the
spec-kit compatibility obligation would make the constitutionally authorized
mechanical removals (speckit skill and dependency cleanup in other phases) a
constitutional violation. The Operator has ratified full retirement of
spec-kit on 2026-06-30.

This spec authorizes the amendment of constitution Principle X from "Spec Kit
Compatibility" to "CE-Native Spec Substrate", reflecting the actual state of
CE's spec substrate. It additionally authorizes subsequent mechanical phases
to remove spec-kit skill files and clean up references — those changes are
governed by this spec as their parent mandate but executed in separate PRs.

## User Scenarios & Testing

### Scenario 1 — Constitution No Longer Mandates Spec-Kit Compatibility (P1)

A reviewer reads the amended constitution and confirms that Principle X no
longer mandates "Creator Engine MUST NOT break Spec-Kit-only workflows." The
new Principle X affirms CE's native spec substrate and permits spec-kit
tooling retirement without constitutional violation.

**Independent Test**: A reviewer with `git clone` reads `.specify/memory/
constitution.md` Principle X and can state clearly that: (a) spec-kit CLI /
skill compatibility is no longer a MUST NOT break obligation; (b) the spec.md
/ plan.md / tasks.md plain-Markdown artifact format remains valid; (c) the
cev3 Scope lifecycle is identified as the native substrate.

**Acceptance Scenarios**:

1. **Given** the amended constitution, **When** a reviewer reads Principle X,
   **Then** they find no clause mandating preservation of spec-kit CLI or
   skill compatibility.
2. **Given** the amended constitution, **When** a reviewer reads Principle X,
   **Then** they find an explicit statement that spec.md / plan.md / tasks.md
   files authored under the spec-kit format remain valid CE input without
   rewriting.
3. **Given** the amended constitution, **When** a reviewer reads Principle X,
   **Then** they find the cev3 Scope lifecycle named as the first-class native
   spec substrate.

---

### Scenario 2 — Amendment Procedure Was Followed (P1)

A reviewer confirms that the constitution's own amendment procedure was
followed: a spec/plan/tasks triple exists under governance, explicit Source
approval is recorded in the amendment commit, and the version bumps from
1.1.0 to 2.0.0 (MAJOR, because the ratified principle is redefined).

**Independent Test**: A reviewer with `git log` and the repository artifacts
can read: (a) this spec/plan/tasks triple in `specs/006-retire-speckit-
principle-x/`; (b) the Source approval record in the Sync Impact Report and
the commit message; (c) the version line in the constitution reads 2.0.0.

**Acceptance Scenarios**:

1. **Given** the repository, **When** a reviewer inspects `specs/006-retire-
   speckit-principle-x/`, **Then** they find spec.md, plan.md, and tasks.md
   that together state the decision, the edit, and the task sequence.
2. **Given** the amendment commit, **When** a reviewer reads the commit
   message and the constitution's Sync Impact Report, **Then** they find an
   explicit record of Source (Operator) approval dated 2026-06-30.
3. **Given** the amended constitution, **When** a reviewer reads the version
   line, **Then** it reads 2.0.0 with Last Amended 2026-06-30.

---

## Requirements

- **R-001**: Principle X MUST be retitled from "Spec Kit Compatibility" to
  "CE-Native Spec Substrate".
- **R-002**: The new Principle X MUST name the cev3 Scope lifecycle
  (Frame → Shape → Build → Review → Ship) as the first-class native
  feature-spec substrate.
- **R-003**: The new Principle X MUST state that the vendored spec-kit
  tooling (CLI, Claude-Code skills, scaffolding) is retired and MUST NOT be
  re-introduced as a new dependency.
- **R-004**: The new Principle X MUST preserve the plain-Markdown artifact
  format (spec.md, plan.md, tasks.md) as the canonical wire format, governed
  natively by CE.
- **R-005**: The new Principle X MUST state that existing spec/plan/tasks
  files authored under the spec-kit format remain valid CE input without
  rewriting.
- **R-006**: The constitution version MUST be bumped to 2.0.0 (MAJOR — a
  ratified principle is redefined).
- **R-007**: The constitution's "Last Amended" date MUST be set to 2026-06-30.
- **R-008**: The Sync Impact Report MUST be updated to record this amendment,
  including the Source approval and prior bump history.
- **R-009**: The governance proposal MUST exist as a spec/plan/tasks triple
  under `specs/006-retire-speckit-principle-x/` before the amendment is
  applied.
- **R-010**: This PR MUST NOT remove spec-kit skill files, spec-kit CLI
  references, or other mechanical artifacts — those are separate phases
  authorized by this spec but executed in subsequent PRs.

## Success Criteria

- **SC-001**: `git grep "Spec Kit Compatibility" .specify/memory/constitution.md`
  returns no output after this amendment.
- **SC-002**: `git grep "CE-Native Spec Substrate" .specify/memory/constitution.md`
  returns a match in the Principle X heading.
- **SC-003**: The version line in `.specify/memory/constitution.md` reads
  `2.0.0`.
- **SC-004**: The Sync Impact Report in the constitution includes a record
  of Source (Operator) approval dated 2026-06-30.
- **SC-005**: `ce validate-pr` passes GREEN with no new test failures.

## Assumptions

- The Operator (Source) ratification of this amendment has been given and is
  recorded in the amendment commit and constitution's Sync Impact Report per
  the constitution's amendment procedure.
- Subsequent mechanical phases (spec-kit skill retirement, reference cleanup)
  are authorized by this spec but are out of scope for this PR.
- The spec.md / plan.md / tasks.md artifact format is stable and CE-owned;
  no format migration is required.
- The cev3 Scope lifecycle naming (Frame → Shape → Build → Review → Ship) is
  the ratified CE-native vocabulary as of 2026-06-30.
