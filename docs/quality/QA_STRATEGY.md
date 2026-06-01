# Creator Engine QA Strategy

**Status**: Canonical. Authored under Sprint 0 Execution Slice A.

**Source-of-truth relationship**: REFERENCE. This document defers
to Feature 001 contracts for substrate verification (FR-025–FR-027a)
and to Feature 002 §Actor/Tool Ownership Matrix for the QA agent
role. The QA agent governed identity record and the QA evidence
schema are deferred to Feature 004 per Feature 002 FR-025; the
release-readiness checklist is deferred to Feature 006. This
strategy is the policy QA must obey when those features land; it
does not author them.

## a. Testing levels

Creator Engine recognizes seven testing levels. The required level
set depends on the mutation class under test (see §b).

- **Unit**: function- or module-level tests with mocked or pure
  inputs. Fast, deterministic, run on every change. The substrate
  validator's `pytest` suite at `validators/tests/` is a unit-level
  test set.
- **Integration**: tests across two or more components within
  Creator Engine (or between Creator Engine and a controlled
  dependency such as Spec Kit), exercising real inter-component
  contracts.
- **End-to-end (e2e)**: tests that walk a complete SDLC scenario or
  a Creator-Engine-governed flow from `Idea/Intent` through
  `Post-release Evidence Recorded` (or a meaningful sub-arc thereof)
  on real artifacts.
- **Security**: tests that exercise the security mutation class and
  redaction gate semantics — for example, that a tenant artifact
  declaring future public export intent is correctly rejected
  without a redaction record (Feature 001 FR-019–FR-021).
- **Accessibility**: tests that exercise human-facing surfaces (PR
  template content, canonical doc readability, error messages). v0.1
  has no UI; accessibility tests apply primarily to the readability
  of governance artifacts and CLI output.
- **Performance**: tests for validator latency, parser throughput on
  realistic example tenants, and offline-install duration. v0.1
  performance bar lives at Feature 001 SC-007 (validator pass on
  bundled examples in under sixty seconds with no network).
- **Regression**: tests that explicitly reproduce previously
  observed failures, including malformed examples per Feature 001
  FR-029 and SC-006.

Levels MAY be combined within a single test file; the classification
governs *which gates the test satisfies*, not *which directory the
test lives in*.

## b. Mapping of testing levels to mutation classes

The level requirement scales with mutation-class risk. The table
below maps the nine baseline classes to the levels required for a
mutation in that class to satisfy Definition of Done (FR-014) and
Sprint 0 / future-feature acceptance criteria.

| Mutation class | Unit | Integration | E2E | Security | Performance | Regression |
|---|---|---|---|---|---|---|
| `docs` | If touched | If touched | — | — | — | If a doc-content regression has been observed |
| `code` | Required | Required (if external surfaces touched) | Required (if SDLC arc affected) | If touching secrets / credentials / public surfaces | If hot path | If reproducing a bug |
| `schema` | Required | Required | If lifecycle states / wrappers touched | If schema authorises a new surface | — | If reproducing a schema bug |
| `deploy` | — | — | Required (when Feature 006 lands) | Required | — | Required |
| `governance` | — | Required (validator behavior) | Required (governed flow rehearsal) | Required (if authority/ratifier rules touched) | — | Required |
| `identity` | — | Required (validator behavior) | Required (identity ↔ authority matrix end-to-end) | Required | — | Required |
| `security` | Required (policy/gate logic) | Required | Required (redaction gate flow) | Required (positive and negative) | — | Required |
| `attestation` | Required (record schema validation) | Required (validator + record store) | Required (record finalization flow) | If attestation authenticates external surface | — | Required |
| `redaction` | Required (policy enforcement) | Required (gate evaluator) | Required (redaction record approval flow + author/approver separation per FR-021) | Required | — | Required |

Interpretation notes:

- "If touched" means: required only when the test surface is
  materially affected by the change.
- Privileged classes (`deploy`, `governance`, `identity`, `security`,
  `attestation`, `redaction`) cluster heavier coverage because their
  failure modes are also the substrate's worst failure modes.
- Performance is required for hot-path code paths; the validator
  performance bar is named via Feature 001 SC-007.

## c. The QA agent role

Per Feature 002 §Actor/Tool Ownership Matrix, the QA agent is
**named in the operating model; governed identity record deferred to
Feature 004**.

- **Presence category**: named with identity record deferred.
- **Allowed instruction sources**: Hermes-authored QA envelopes
  (defined once Feature 004 instantiates the role); QA gate
  definitions referenced from this document.
- **Allowed mutation classes**: `docs` (QA evidence records and
  triage notes); never `code`, `schema`, or any privileged class.
- **Allowed communication surfaces**: QA evidence records (schema
  deferred to Feature 004); test result logs; flaky-test triage
  notes; release-readiness check results attached to a PR or
  attestation.
- **Required ratifier**: Hermes verifies QA evidence presence;
  Source ratifies any change that weakens a QA gate (a
  `governance`-class privileged mutation per Feature 001 FR-008).
- **Required audit artifacts**: QA evidence records (schema deferred
  to Feature 004) linked to the SDLC transition the QA pass
  authorizes.
- **Phase 1 authority**: deferred to Feature 004 for instantiation;
  Feature 002 names the role and reserves its surfaces.
- **Phase 2-eligible authority**: under a future Source-ratified
  policy, QA evidence pass may be a precondition for auto-merge of
  non-privileged classes; QA never ratifies privileged classes.
- **Prohibited actions**: ratifying QA gates for privileged classes;
  merging; weakening QA gates; consuming envelopes outside the
  envelope-scoped QA work range.

Until Feature 004 instantiates the QA agent identity record,
Nefarious/Hermes performs QA-relevant audits as part of the T14–T18
verification chain. The post-Feature-004 QA agent inherits these
duties without expanding mutation authority.

## d. QA evidence schema (Feature 004 deferral)

The QA evidence record schema is deferred to Feature 004 (Independent
Review / QA Agent Evidence). Per Feature 002 FR-021, this document
flags the dependency rather than inventing a competing contract.

Until Feature 004 lands, QA evidence is captured in repository-visible
artifacts per constitution Principle VIII:

- Validator outputs from `python -m creator_engine_validator
  check-examples` and `... scan-no-limitless`.
- `pytest` outputs from `validators/tests/`.
- Reviewer findings recorded on the PR (review-only; never
  ratification for privileged classes).
- Flaky-test triage notes attached to the PR or to the relevant
  attestation drafting note.

Post-Feature-004, the QA evidence record will be a YAML file under
the tenant's Feature 004-declared QA evidence path (analogous to the
attestation / ratification / redaction record stores at FR-020a) and
will link to the SDLC transition (typically T16 or T17 as Feature 004
specifies).

## e. Flaky-test triage policy

A test is "flaky" if it has passed and failed on the same code under
identical inputs more than once in the last thirty days (or the
local equivalent observation window).

- **Detection**: CI run logs, local re-run logs, and reviewer
  observation.
- **Triage**: Hermes (pre-Feature-004) or QA agent (post-Feature-004)
  records the flaky test in a triage note linked to the relevant
  spec, plan, or tasks artifact.
- **Resolution paths**:
  1. **Fix the test**: the preferred resolution. The fix is a
     `code`-class mutation requiring its own envelope, evidence, and
     ratification per §b.
  2. **Quarantine** (skip) **with a recorded expiry**: temporary
     quarantine is permitted only when the quarantine ticket is
     committed alongside the skip and the expiry condition is
     explicit (e.g., "remove after Feature 004 schema lands"). A
     quarantine without an expiry is itself a governance failure;
     the quarantine PR MUST be reviewed against this policy.
  3. **Delete the test**: only if the underlying behavior is no
     longer required (a `code` or `schema` mutation in its own
     right) and the deletion is recorded.
- **Prohibited shortcuts**: silently rerunning a failing test until
  it passes; widening the test scope to hide the failure; weakening
  the assertion. Each is itself a governance failure.

## f. Release-readiness checklist (Feature 006 deferral)

The release-readiness checklist is deferred to Feature 006 (Release /
Deployment Governance). Per Feature 002 FR-021, this document flags
the dependency rather than inventing a competing contract.

Until Feature 006 lands, release readiness for Creator Engine
v0.1-docs is satisfied by the Sprint 0 exit gates enumerated in
[`../../specs/sprint-0-minimum-viable-delivery-system/README.md`](../../specs/sprint-0-minimum-viable-delivery-system/README.md)
§4. Slice A of Sprint 0 (this batch) advances only the canonical-docs
gate.

Post-Feature-006, the release-readiness checklist will include:

- Pre-merge attestation present per FR-004.
- Ratification record present and Source-authored for privileged-class
  mutations per FR-008.
- CI evidence present (post-Feature-003).
- Independent review evidence present (post-Feature-004); review
  evidence is NEVER ratification for privileged classes.
- Deploy ratification record present per FR-008 (T22).
- Rollback evidence requirements satisfied per Feature 006.
- Observability requirements satisfied per Feature 006.

The release-readiness checklist itself is a `governance`-class
artifact and its content is Source-ratified.

## g. Behavioral QA vs. maintainability review

Behavioral QA (this document) and **maintainability review**
([`./MAINTAINABILITY_DEEP_REVIEW.md`](./MAINTAINABILITY_DEEP_REVIEW.md),
[`../delivery/CODE_QUALITY_REVIEW_CHECKLIST.md`](../delivery/CODE_QUALITY_REVIEW_CHECKLIST.md))
are complementary and orthogonal dimensions:

- **Behavioral QA asks: does it work?** The seven testing levels (§a)
  and the level-to-mutation-class mapping (§b) verify that a change
  behaves correctly — unit, integration, e2e, security, accessibility,
  performance, regression.
- **Maintainability review asks: is it well-structured?** It judges
  decomposition, branching, schema/type boundaries, layer placement,
  helper reuse, and atomicity, and it can raise a blocking
  **structural regression**.

The two are evaluated independently, and neither erases the other:

1. **QA / test success does not erase a structural review blocker.** A
   green test run, a green CI run, or a passing validator run is
   behavioral verification; it does **not** clear a blocking
   maintainability finding. A change that passes every test but worsens
   the structure is a structural regression and blocks the review gate
   ([`../delivery/REVIEW_GATE.md`](../delivery/REVIEW_GATE.md) §i.5,
   §o).
2. A maintainability block does not, by itself, imply a behavioral
   defect, and a behavioral defect is not, by itself, a maintainability
   finding; each is recorded under its own gate.
3. Neither QA evidence nor review evidence is Source ratification. Both
   are advisory/governance evidence with no merge, deploy,
   branch-protection, or repository-settings authority.

This section names the QA-vs-maintainability boundary; it adds no
testing level, no mutation-class mapping, and no schema. The QA agent
identity and QA evidence schema remain deferred to Feature 004 per §c
and §d.

## Acceptance posture for this document

This QA_STRATEGY.md satisfies Feature 002 Canonical Document
Specification #13: the testing-level-to-mutation-class table covers
all nine baseline classes; the QA agent role appears in the
Actor/Tool Ownership Matrix and is summarized here; Feature 004 and
Feature 006 deferrals are flagged per FR-021 without inventing
competing contracts. It additionally distinguishes behavioral QA from
maintainability review and states that QA/test success does not erase a
structural review blocker (§g).
