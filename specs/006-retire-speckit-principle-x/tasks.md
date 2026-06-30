---
description: "Tasks for spec-kit retirement Phase 4 — amend constitution Principle X"
---

# Tasks: Retire Spec-Kit — Amend Constitution Principle X

**Input**: `specs/006-retire-speckit-principle-x/spec.md` and `plan.md`
**Mutation class**: governance
**Source (Operator) approval**: Ratified 2026-06-30

## Organization

Single-batch governance amendment. Tasks are ordered (not parallelizable:
the triple must exist before the amendment; the carriers require the
amendment to be complete for the path set to be stable).

---

## Phase 1: Governance Proposal (this triple)

- [X] T001 Create `specs/006-retire-speckit-principle-x/` directory
- [X] T002 Author `spec.md` — decision, scenarios, requirements, success
  criteria, assumptions; mutation class `governance`, Source approval recorded
- [X] T003 Author `plan.md` — before/after diffs for constitution, version
  bump rationale, authorized subsequent phases, deliverables list, gates
- [X] T004 Author `tasks.md` — this file; ordered task list for the
  governance amendment

---

## Phase 2: Constitution Amendment

- [X] T005 Replace Principle X heading and body in `.specify/memory/
  constitution.md`: retitle from "Spec Kit Compatibility" to "CE-Native Spec
  Substrate"; replace body text per plan.md diff.
- [X] T006 Update version line in `.specify/memory/constitution.md` from
  `1.1.0` to `2.0.0` and "Last Amended" from `2026-05-11` to `2026-06-30`.
- [X] T007 Replace the Sync Impact Report HTML comment at the top of
  `.specify/memory/constitution.md` to reflect 1.1.0 → 2.0.0 change,
  record Source (Operator) approval dated 2026-06-30, and move prior 1.1.0
  changes into "Prior bump history".

---

## Phase 3: Carriers

- [X] T008 Generate `.ce/changelog/ce-speckit-retire-principle-x.md` via
  `carrier_gen.write_carriers()` API (kind: changed, scope: governance
  constitution, issue: ce-ops#364 or local).
- [X] T009 Generate `.ce/pr-manifests/ce-speckit-retire-principle-x.md` via
  the same API call; carrier stem must equal branch slug
  `ce-speckit-retire-principle-x`; carrier must include itself in the path
  set.
- [X] T010 Verify declared work class line appears exactly once in the
  carrier: `- **Declared work class:** story`

---

## Phase 4: Preflight and Push

- [X] T011 Run `TMPDIR=/var/tmp ce validate-pr` in ONE pass; confirm GREEN
  with no new failures.
- [X] T012 Commit all changes on branch `ce-speckit-retire-principle-x` with
  a commit message that records Source (Operator) approval in the body.
- [X] T013 Push branch; report HEAD SHA, validate-pr summary line, before/
  after Principle X text, and any hash gate touched. STOP — do not open PR,
  do not merge.

---

## Out of Scope (Authorized But Deferred to Subsequent PRs)

- Removal of `.claude/skills/speckit-*` skill directories
- Removal of speckit from `.specify/extensions.yml`
- Removal of speckit extension files under `.specify/extensions/`
- Cleanup of speckit references in playbooks or docs

Each of those phases cites this spec as its parent mandate.
