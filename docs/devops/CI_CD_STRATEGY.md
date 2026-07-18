# Creator Engine CI / CD Strategy

**Status**: Canonical. Authored under Sprint 0 Execution Slice A.

**Source-of-truth relationship**: REFERENCE. Feature 003 ratifies CI
workflow content; this document specifies the policy CI must obey.
The verifies-not-ratifies invariant lives at Feature 002 FR-013 and
is restated below as the load-bearing rule.

## a. Verifies-not-ratifies invariant (Feature 002 FR-013)

**CI verifies; CI does NOT ratify.**

CI runs tests, lint, typecheck, build, the Creator Engine validator,
and schema validation, and emits status checks and run logs. Those
artifacts become attestation evidence per
[`../governance/ATTESTATION_MODEL.md`](../governance/ATTESTATION_MODEL.md);
they never become a ratification record.

Consequences:

- A green CI run is NOT, by itself, merge authorization. Per Feature
  001 FR-018, a "go ahead" on a surface that the ratification flow
  has not designated as a valid ratification surface for the
  relevant mutation class does not authorize merge, deploy,
  publish, or any other reserved-restricted action. CI status
  checks are not designated ratification surfaces.
- A green CI run is also NOT, by itself, a Definition-of-Done
  finding. Definition of Done (Feature 001 FR-014) requires
  evidence AND author/approver-separated ratification; CI provides
  evidence only.
- A red CI run is, by definition, a Definition-of-Done failure: the
  recorded evidence shows that required checks failed. The
  mutation cannot advance past T17 (CI Evidence Complete) until the
  red run is resolved.
- Agents (Claude Code, Codex, future QA/security/release agents)
  MUST NOT treat CI status as ratification. CI is mechanical
  validation; agent-authored review text is review evidence;
  neither substitutes for human ratification (Feature 001 FR-017;
  Feature 002 FR-013).

## b. Historical Sprint 0 CI check baseline

The following records the v0.1/Sprint 0 policy baseline. All check names,
future-feature expectations, and reproducibility language in this section are
historical; this section does not define today's required CI gate inventory. See
the [CI/CD efficiency audit](CI_CD_EFFICIENCY_AUDIT.html) for the sole current
observed local/CI gate inventory and its fidelity gaps.

The required check set for v0.1 was:

| Check | Purpose | Source |
|---|---|---|
| `pytest` on `validators/tests/` | Validator self-tests (well-formed and malformed examples). | Feature 001 FR-025–FR-027. |
| Lint on validator source (e.g., `ruff` or equivalent) | Style and correctness lint. | Engineering practice. |
| Typecheck on validator source (e.g., `mypy` or equivalent) | Static type safety on the validator. | Engineering practice. |
| Build of validator and any future packaged artifacts | Confirm the package builds offline from the wheelhouses. | Feature 001 FR-026. |
| `python -m creator_engine_validator check-examples` | Validator pass on bundled examples. | Feature 001 FR-025, SC-006, SC-007. |
| `python -m creator_engine_validator scan-no-limitless` | Tenant-identifier leak scan on generic-contract paths (current command name retained from Feature 001). | Feature 001 FR-024, FR-024a, SC-004. |
| Schema validation against `schemas/*.schema.yaml` | Substrate schema integrity. | Feature 001 FR-027. |

Additional checks MAY be required for future-feature batches:

- Feature 003: PR template presence and content; branch protection
  policy linting (if a structured form is adopted).
- Feature 004: review-evidence-record and QA-evidence-record schema
  checks once those schemas land.
- Feature 005: dispatcher / worktree / sandbox integration smoke
  tests.
- Feature 006: deploy-attestation, rollback-evidence, and
  post-release-evidence schema checks once those schemas land.

The baseline check set was required to be reproducible offline from a fresh
`git clone` per Feature 001 FR-026. Before Feature 003 wired CI workflows, the
same checks ran locally per
[`../../validators/README.md`](../../validators/README.md).

## c. Protected branch policy summary (historical Feature 003 baseline)

This section records the protected-branch policy baseline authored before
Feature 003 instantiated repository CI. Feature 003 has since delivered the
validation workflow; the [CI/CD efficiency audit](CI_CD_EFFICIENCY_AUDIT.html)
records the current observed gate inventory. The authority and required-check
obligations below remain current policy.

Branch protection is a live GitHub settings mutation. Per Feature
001 FR-008, changes to branch protection, environment gates, or
merge policy are themselves privileged
`governance`/`security`/`deploy`-class mutations that require Source
ratification.

The policy CI must enforce:

- The canonical branch (typically `main`) MUST require:
  - At least one approving review distinct from the PR author.
  - All required CI checks for the candidate passing.
  - A signed-off pre-merge attestation linked from the PR.
  - For privileged-class PRs, a Source ratification record linked
    from the PR.
- Force-push to the canonical branch is prohibited.
- Direct commits to the canonical branch (bypassing PR) are
  prohibited except for Source-ratified emergency exceptions; such
  exceptions are themselves a ratified governance mutation.
- Branch-protection changes are themselves a governance mutation;
  changing protection rules without Source ratification is an
  `authority` conflict per Feature 002 FR-018.

Before Feature 003 applied these as GitHub settings, the policy was enforced
as repo-visible policy here. The historical manual checklist confirming
protection equivalents lives in the Sprint 0 exit gates per
[`../../specs/sprint-0-minimum-viable-delivery-system/README.md`](../../specs/sprint-0-minimum-viable-delivery-system/README.md)
§4.

## d. CI mutation-class ratification policy

Per Feature 001 FR-008, the `governance`, `security`, and `deploy`
mutation classes require explicit human ratification. CI policy
changes — workflow files, required-check lists, branch-protection
configuration — are themselves privileged mutations under one or more
of these classes:

- Adding, removing, or changing a CI check, or weakening the
  required-check set, is a `governance` (and often `security`)
  mutation.
- Changing the deploy pipeline or any deploy automation is a
  `deploy` mutation.
- Changing CI's access to credentials, secrets, or registries is a
  `security` mutation.

Any such change MUST be authored under a Hermes-authored envelope,
ratified by Source, and recorded with a ratification record per
Feature 001 FR-016 and FR-020a. The CI workflow itself never
ratifies a change to itself; Source ratifies, and CI then executes
the ratified workflow.

## e. CI evidence linkage to SDLC transition T17

The operating model's SDLC Transition Matrix attaches CI evidence to
T17 (Independent Review Complete → CI Evidence Complete):

- The required evidence at T17 is the CI status check records and
  validator outputs per Feature 002 §SDLC Transition Matrix.
- T17 advances only after every required check for the candidate has passed.
- A red CI run halts at T17 until resolved; the mutation does NOT
  advance to T18 (Scope Audit Complete) on stale or skipped CI
  evidence.
- CI evidence becomes an input to the pre-merge attestation drafted
  at T15 / finalized after T20; it never becomes the ratification
  record itself.

The CI evidence linkage is bidirectional with
[`../governance/ATTESTATION_MODEL.md`](../governance/ATTESTATION_MODEL.md):
the attestation record cites the CI evidence; the CI evidence is
discoverable from the attestation record's `verification evidence`
field.

## f. Explicit Feature 003 deferral

This section records the Sprint 0 Slice A historical snapshot. Feature 003 has
since delivered `.github/workflows/validate.yml`; see the
[CI/CD efficiency audit](CI_CD_EFFICIENCY_AUDIT.html) for the current gate inventory.

At that historical epoch, the following surfaces were deferred to Feature 003
(GitHub CI Governance):

- `.github/workflows/` baseline validation workflow.
- PR template content and its activation.
- Branch protection settings as live GitHub configuration.
- Required-check list as enforced by GitHub.
- Review policy and/or CODEOWNERS policy where applicable.
- CI run reporting integration (status badges, summary surfaces).

No `.github/` workflow content was authored in Slice A of Sprint 0
Execution. At that epoch, the Sprint 0 exit gate "Baseline PR validation exists
through GitHub Actions, or Source ratifies a temporary repo-visible
exception" remained pending until Feature 003.

## Acceptance posture for this document

This CI_CD_STRATEGY.md satisfies Feature 002 Canonical Document
Specification #15 as authored at the Sprint 0 epoch: the
verifies-not-ratifies invariant is explicit; the historical Feature 003
deferral is explicit; CI evidence linkage to T17 is stated; no `.github/`
workflow content was authored by that slice.

## CI efficiency audit

The repository-native [CI/CD efficiency audit](CI_CD_EFFICIENCY_AUDIT.html)
maps shared local/CI gates, records known fidelity gaps, and separates observed
evidence and technical-risk assessments from proposals that remain subject to
the existing ratification and change-control contract.
