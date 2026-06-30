# Implementation Plan: Retire Spec-Kit — Amend Constitution Principle X

**Branch**: `ce-speckit-retire-principle-x` | **Date**: 2026-06-30
**Spec**: [spec.md](./spec.md)
**Mutation class**: governance
**Source (Operator) approval**: Ratified 2026-06-30

## Summary

Amend `.specify/memory/constitution.md` to retire Principle X ("Spec Kit
Compatibility") and replace it with Principle X ("CE-Native Spec Substrate"),
reflecting that CE's cev3 Scope lifecycle is the native, first-class spec
substrate and the vendored spec-kit tooling is retired. Bump the constitution
version from 1.1.0 to 2.0.0 (MAJOR: backward-incompatible redefinition of a
ratified principle). Record Source (Operator) ratification in the Sync Impact
Report and the amendment commit. Create the governance spec/plan/tasks triple
that the constitution's own amendment procedure requires.

This plan does NOT cover mechanical removal of spec-kit skill files, CLI
references, or other dependency cleanup — those are separate phases authorized
by the accompanying spec but executed in subsequent PRs.

## Constitution Edit — What Changes

### Principle X text (`.specify/memory/constitution.md` lines ~194–204)

**Before (to be removed):**
```
### X. Spec Kit Compatibility

Spec Kit is the first supported feature-spec substrate. Creator Engine wraps
Spec Kit artifacts (spec.md, plan.md, tasks.md, constitution.md) with
identity, governance, attestation, and ratification metadata. Creator Engine
MUST NOT break Spec-Kit-only workflows; a spec authored against vanilla Spec
Kit MUST remain readable and usable.

**Rationale**: Replacing Spec Kit would force tenants to choose. Wrapping it
lets tenants adopt Creator Engine incrementally, on top of an existing spec
substrate they already understand.
```

**After (replacement):**
```
### X. CE-Native Spec Substrate

CE's own cev3 Scope lifecycle (Frame → Shape → Build → Review → Ship) is the
first-class, native feature-spec substrate. The artifact format — plain
Markdown files named spec.md, plan.md, and tasks.md — remains the canonical
wire format; Creator Engine governs these artifacts natively without the
vendored spec-kit tool or its skill layer. The vendored spec-kit tooling has
been retired; CE workflows and CI gates MUST NOT introduce new dependencies on
the spec-kit CLI, spec-kit Claude-Code skills, or spec-kit scaffolding
commands.

Existing spec.md, plan.md, and tasks.md files authored under the spec-kit
convention remain valid input to CE workflows without rewriting, because CE
governs the artifact format — not the tool that originally authored it.

**Rationale**: The cev3 Scope lifecycle (Frame→Shape→Build→Review→Ship) gives
CE a native, governed, full-lifecycle spec substrate. The vendored spec-kit
dependency was an external tool layer that added drift risk without adding
governance value. Retiring it eliminates a maintenance obligation and aligns
the constitution with the system CE has actually become.
```

### Version line (`.specify/memory/constitution.md` last line)

**Before:** `**Version**: 1.1.0 | **Ratified**: 2026-05-08 | **Last Amended**: 2026-05-11`
**After:** `**Version**: 2.0.0 | **Ratified**: 2026-05-08 | **Last Amended**: 2026-06-30`

### Sync Impact Report (top HTML comment)

Replace the existing Sync Impact Report with a new one that:
- States version change 1.1.0 → 2.0.0
- Gives the MAJOR bump rationale (Principle X redefined)
- Names the modified principle
- Moves the prior 1.1.0 changes into "Prior bump history"
- Records Source (Operator) approval dated 2026-06-30

## Version Bump Rationale

Per the constitution's versioning policy:

> **MAJOR**: Backward-incompatible removal or redefinition of a principle, or
> a change that invalidates existing attestations, governance flows, or
> ratifier authority models.

This change redefines Principle X. Any governance plan, spec, or attestation
that cited Principle X as a Spec-Kit compatibility mandate is invalidated by
this amendment (those plans are now authorized, not constrained). MAJOR bump
is required.

## Authorizing Subsequent Phases

This amendment constitutionally authorizes the following subsequent PRs
(separate scope, each needing its own carrier):

- Mechanical removal of `.claude/skills/speckit-*` skill directories
- Removal of speckit references in `.specify/extensions.yml` and related
  `.specify/extensions/` files
- Removal of speckit skill references in other playbooks or docs

Each subsequent phase must cite this spec (`specs/006-retire-speckit-
principle-x/spec.md`) as its parent mandate.

## Deliverables for This PR

1. `specs/006-retire-speckit-principle-x/spec.md` — governance proposal
2. `specs/006-retire-speckit-principle-x/plan.md` — this file
3. `specs/006-retire-speckit-principle-x/tasks.md` — task list
4. `.specify/memory/constitution.md` — amended (Principle X, version, Sync
   Impact Report)
5. `.ce/changelog/ce-speckit-retire-principle-x.md` — per-PR changelog
6. `.ce/pr-manifests/ce-speckit-retire-principle-x.md` — path-manifest carrier

## Gates

- `ce validate-pr` must pass GREEN in one pass (TMPDIR=/var/tmp hermetic)
- No spec-kit skills may be removed in this PR (separate phases)
- Carrier stem must equal branch slug `ce-speckit-retire-principle-x`
- Declared work class: `story`
