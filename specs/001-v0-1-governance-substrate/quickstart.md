# Quickstart: Creator Engine v0.1 Governance Substrate

**Phase**: 1 (Design & Contracts) | **Date**: 2026-05-09

This quickstart describes how a reviewer or auditor exercises the
substrate end-to-end on a fresh `git clone`, with no network. It is
written against the v0.1 deliverables enumerated in plan.md; the steps
become executable as those deliverables land.

The five governance questions the substrate answers (SC-001) are listed
inline as **Q1..Q5** so a reviewer can map each step to the question it
answers.

## Prerequisites

- `git` and Python 3.11 available locally.
- A fresh checkout of this repository: `git clone <url> creator-engine
  && cd creator-engine`.
- A virtualenv with the validator's pinned dependencies installed from
  the checked-in offline wheelhouse:
  `python -m venv .venv && source .venv/bin/activate && pip install
  --no-index --find-links validators/wheelhouse -r validators/requirements.txt`.

No other tooling, no network access during validation or dependency
installation, no SaaS accounts (FR-026, principle II).

## 1. Walk an identity record (Q1: identity)

Open the LIMITLESS dogfood identity record:

```text
tenants/limitless/identity-record.yml
```

Confirm the record names: `tenant_id`, `source_host`,
`source_host_installation_id`, `agent_app_slug`, `agent_actor_id`,
`runtime_tool`, `role_category`, `authority_context`,
`human_ratifier_roles` (non-empty), `mutation_classes`,
`allowed_repositories`, `signing_policy`,
`attestation_storage_path`, `ratification_storage_path`, and
`redaction_storage_path` (FR-001).

> **Q1 satisfied** when the reviewer can name the tenant, source host,
> agent app, agent actor, allowed repos, and signing policy from this
> file alone (US1 AS1, SC-001).

## 2. Walk a spec wrapper sidecar (Q2: spec format)

Open the project-agnostic example pair:

```text
examples/well-formed/spec.md
examples/well-formed/spec.creator-engine.yml
```

Confirm the sidecar declares `id`, `title`, `tenant`, `owner_role`,
`status`, `spec_type` (one of the seven taxonomy values per FR-011),
`mutation_class`, `permitted_actions`, `scope`, `acceptance_criteria`,
`verification`, `ratification_required`, and `identity_policy_ref`
(FR-009, FR-012a).

Confirm `spec.md` is byte-identical to vanilla Spec Kit Markdown — no
Creator Engine fields appear in its body or frontmatter (FR-010,
US2 AS4).

> **Q2 satisfied** when the reviewer sees governance metadata in the
> sidecar and only the sidecar.

## 3. Walk the authority matrix and ratification flow (Q3: ratifier)

Open:

```text
docs/contracts/authority-matrix.md
docs/contracts/ratification-flow.md
tenants/limitless/authority-matrix-overlay.yml
tenants/limitless/ratification-flow.yml
```

Pick any baseline mutation class from the matrix
(`docs / code / schema / deploy / governance / identity / security /
attestation / redaction`). Confirm the matrix names the
`required_ratifier_role`, the `allowed_communication_surfaces`, and the
`required_audit_artifacts` for that class. Confirm the
ratification-flow file lists `valid_ratification_surfaces` and
`evidence_required` for the same class.

For an FR-008 privileged class (e.g. `deploy`), confirm the
`required_ratifier_role` resolves to a *human* role.

> **Q3 satisfied** when the reviewer can state, for any class, who
> must ratify, on what surface, with what evidence, and that the
> implementer is barred from self-ratifying (US3 AS2).

## 4. Walk an attestation record and verification evidence (Q4 + Q5: evidence + attestation)

Open:

```text
examples/well-formed/attestations/2026-05-09-EX-MUT-001.yml
examples/well-formed/ratifications/2026-05-09-EX-MUT-001.yml
```

Confirm the attestation record contains: `mutation_id`, `state` (one
of `pre_merge` or `finalized`), `spec_ref`, `agent_identity_ref`,
`mutation_class`, `permitted_actions`, `verification_evidence`
(`method`, `evidence_refs`), `ratifier_identity_ref`, and `created_at`
matching the filename (FR-004, FR-020a). When `state == finalized`,
confirm `merge_reference` is populated.

Confirm the ratification record's `mutation_id` matches the
attestation's, that the `surface` is among the ratification flow's
`valid_ratification_surfaces`, and that the `ratifier_actor_id` is
distinct from the spec's author (FR-007).

> **Q4 satisfied** when the reviewer reads off the verification
> evidence (changed files, checks run, review findings, approval
> state) from the attestation record alone (US4 AS1).
>
> **Q5 satisfied** when the same record names the spec, agent
> identity, mutation class, permitted-actions list, and ratifier
> identity, and resolves all of them to repository content with no
> external system (US4 AS3, SC-001).

## 5. Run the validator on the well-formed example

```text
python -m creator_engine_validator check-examples
```

Expected output: `examples/well-formed/` passes; `examples/malformed/`
fails with one citation per intentional defect, each citing the
violated FR (e.g. `FR-001` for the missing-fields identity record,
`FR-013` for the missing-acceptance spec sidecar, `FR-013a` for the
skipped-state lifecycle, `FR-007` for the self-ratification record,
FR-027a for the duplicate spec id and the class/action mismatch,
FR-020 for the missing redaction-policy version).

Confirm `check-examples` exits `0` when both expected outcomes are
observed. To inspect raw validation exit codes separately, run
`python -m creator_engine_validator check examples/well-formed/` and
confirm exit code `0`, then run `python -m creator_engine_validator
check examples/malformed/` and confirm exit code `1`. Confirm the full
pass completes in under 60 seconds on a fresh checkout (SC-006,
SC-007).

## 6. Run the no-LIMITLESS-strings scan (FR-024 / SC-004)

```text
python -m creator_engine_validator scan-no-limitless
```

The validator loads
`tenants/limitless/limitless-identifiers.yml`, then performs an
exact-substring search of every file under `docs/contracts/`,
`schemas/`, `validators/`, and `templates/`. Expected output: `0
matches`, exit code `0` (SC-004).

A reviewer can re-run the scan against any later commit and trust the
result is reproducible: the identifier list is in-tree and
authoritative.

## 7. Walk the LIMITLESS dogfood mapping (Q1–Q5 in tenant)

Repeat steps 1–4 against the LIMITLESS fixture instead of the
project-agnostic example. Confirm:

- All identity record fields are populated; zero fields contain
  placeholder, deferred, or unresolved values (SC-005).
- The LIMITLESS authority matrix overlay supplies tenant-specific role
  names without modifying the generic baseline rows (FR-015).
- The validator reports a clean pass on the LIMITLESS fixture (US6
  AS1).

## 8. Walk a malformed example end-to-end (US7 AS2)

Pick `examples/malformed/spec.creator-engine.missing-acceptance.yml`.
Run:

```text
python -m creator_engine_validator check examples/malformed/
```

Confirm the validator exits non-zero and emits an error citing the
violated contract clause (FR-013) and the specific missing field
(`acceptance_criteria`).

Repeat for at least one example per major contract (identity,
spec/plan/tasks sidecar, attestation, ratification, redaction,
lifecycle, mutation-class) per FR-029.

## 9. Walk the verification spec (self-dogfood at meta level)

Open the governed verification-spec source pair:

```text
docs/contracts/verification-spec/spec.md
docs/contracts/verification-spec/spec.creator-engine.yml
```

Then open the rendered contract document:

```text
docs/contracts/verification-spec.md
```

Confirm the verification spec is itself a Creator-Engine-governed
artifact using the canonical sidecar filename (FR-031) and that its
governance fields validate against the v0.1 wrapper schema (FR-009,
FR-012a). This is the substrate eating its own dogfood at the meta
level without introducing any non-canonical sidecar discovery rule.

## What this quickstart does NOT cover

- Public/NDA-visible export workflows. v0.1 defines the redaction
  gate as policy-and-validation only (FR-019, principle XII); no
  export pipeline exists.
- Live source-host enforcement (e.g. PR check that runs the validator
  in CI). v0.1 is repo-runnable only (FR-026, FR-027a v0.1
  exclusion).
- Multi-tenant SaaS, dashboards, drift detection. Out of scope per
  principle XI (YAGNI).

## Mapping back to user stories

| Quickstart step | Spec user story | Spec acceptance scenario |
|-----------------|-----------------|--------------------------|
| 1               | US1             | AS1, AS2, AS3            |
| 2               | US2             | AS1, AS2, AS3, AS4       |
| 3               | US3             | AS1, AS2, AS3, AS4       |
| 4               | US4             | AS1, AS2, AS3, AS4       |
| 5               | US7             | AS1, AS2, AS3            |
| 6               | US6             | AS2 (no-LIMITLESS), SC-004 |
| 7               | US6             | AS1, AS3                 |
| 8               | US7             | AS2                      |
| 9               | (FR-031 self-dogfood) | — |

If a reviewer can complete steps 1–9 on a fresh clone with no
network, the v0.1 substrate has met its acceptance bar.
