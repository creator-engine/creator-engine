# Creator Engine Testing Strategy

**Status**: Canonical. Authored under Sprint 0 Execution Slice A.

**Source-of-truth relationship**: REFERENCE. This document defers to
Feature 001 Definition of Done (FR-014) and validator requirements
(FR-025–FR-027a), and to the verifies-not-ratifies invariant at
Feature 002 FR-013. At the Sprint 0 authoring epoch, CI execution was deferred
to Feature 003; this document specifies the testing posture CI must obey.

This document is the engineering-practice complement of
[`./QA_STRATEGY.md`](./QA_STRATEGY.md). The QA strategy says *which
testing levels are required for which mutation classes*; this
strategy says *how engineers write, place, and capture evidence from
those tests*.

## a. When test writing is mandatory

A change MUST ship with tests when any of the following holds:

- **Feature 001 FR-025 trigger**: the change adds, modifies, or
  removes substrate validator behavior, spec wrapper conformance,
  identity-record completeness, mutation-class declaration
  enforcement, Definition-of-Ready / Definition-of-Done field
  presence, or any other contract that the Creator Engine validator
  enforces.
- **SDLC transition T14 trigger** (operating-model side): the change
  advances any in-flight mutation to `Local Validation Complete`.
  T14's authorizing gate is "every `required_validation` command in
  the envelope passes," and the consumer cannot satisfy that gate
  without recorded validator outputs.
- **Mutation-class trigger**: per
  [`./QA_STRATEGY.md`](./QA_STRATEGY.md) §b, the mutation class
  imposes test-level requirements (e.g., `code` requires unit and
  often integration; `security` requires positive and negative
  tests).
- **Regression trigger**: the change reproduces or fixes a
  previously observed failure. A regression test is mandatory; a
  fix without a regression test invites recurrence.

A change MAY ship without new tests only when:

- the change is a `docs`-only mutation that does not touch a
  validator-visible surface and is not authored to satisfy a
  validator-relevant rule, AND
- the existing test suite covers the surfaces the change touches,
  AND
- the change is not satisfying a regression trigger.

When `code` or `schema` is touched in a way that affects a Feature
001 validator surface, tests are not optional regardless of the
size of the diff.

## b. Test placement convention

Test placement is convention, not contract. The substrate today
ships tests under `validators/tests/` and runs them via
`PYTHONPATH=validators ${CE_VALIDATOR_PYTHON:-python} -m pytest validators/
tests -q` (per
[`../../validators/README.md`](../../validators/README.md)).

The convention:

- **Substrate-development tests** live under `validators/tests/` and
  exercise the offline validator. These tests are the
  v0.1 acceptance bed: every Feature 001 validator check has at
  least one well-formed example test and one deliberately malformed
  example test (FR-028, FR-029, SC-006).
- **Tenant tests** (when tenants ship their own tests) live under
  `tenants/<name>/tests/` or per the tenant's local convention; they
  are not part of the substrate's validator suite and MUST NOT
  introduce tenant-specific identifiers into substrate-test paths
  per Feature 001 FR-024.
- **Future product code tests** (Features 003 onward) land under
  paths their respective specs declare; place tests adjacent to the
  code they exercise unless a tenant/substrate boundary forces
  separation.

Test data lives next to the test that consumes it (e.g., fixtures
under `validators/tests/fixtures/` or via the bundled examples
under `examples/`).

## c. Validator self-tests (Feature 001 FR-025–FR-027)

The Creator Engine validator is itself subject to the substrate's
testing requirements. Every validator check ships with:

- A **well-formed example** that the check accepts (FR-028, SC-006).
- A **deliberately malformed example** that the check rejects with a
  specific, contract-referenced error (FR-027, FR-029, SC-006).
- An **acceptance assertion** in `validators/tests/` that exercises
  both examples and asserts the validator's exit code and reported
  error per FR-027 ("with a contract-referenced error citing the
  specific field or rule violated").

The validator MUST run from a fresh `git clone` without external
service calls (FR-026); the offline install procedure in
[`../../validators/README.md`](../../validators/README.md) is the
authoritative install path.

Per Feature 001 SC-007, the validator's full pass on the bundled
examples MUST complete in under sixty seconds on a developer
workstation with no external network requests. Performance
regressions are themselves test failures.

## d. CI verification expectations (historical Feature 003 baseline)

CI is mechanical validation. CI verifies; CI does NOT ratify. The following
was the expected v0.1/Sprint 0 check baseline recorded in
[`../devops/CI_CD_STRATEGY.md`](../devops/CI_CD_STRATEGY.md) §b:

- `pytest` on `validators/tests/`.
- Lint and typecheck on the validator source.
- Build artifacts (where applicable).
- Creator Engine validator on the bundled examples
  (`python -m creator_engine_validator check-examples`).
- Tenant-identifier leak scan (current command name retained from
  Feature 001) (`python -m creator_engine_validator scan-no-limitless`).
- Schema validation against `schemas/*.schema.yaml`.

The [CI/CD efficiency audit](../devops/CI_CD_EFFICIENCY_AUDIT.html) is the sole
current observed local/CI gate inventory. At the Sprint 0 epoch, CI workflow
content (`.github/workflows/`) and check definitions were deferred to Feature
003, and the same baseline ran locally per the offline install in
[`../../validators/README.md`](../../validators/README.md). The
operating-model SDLC transition T17 remains in force; before CI was wired, its
evidence was captured manually (`pytest -q` output, validator output) and
attached to the pre-merge attestation per
[`../governance/ATTESTATION_MODEL.md`](../governance/ATTESTATION_MODEL.md)
§a.

CI changes are themselves a privileged
`governance`/`security`/`deploy` mutation per Feature 001 FR-008.
Tests covering CI configuration were assigned to the Feature 003 batch.

## e. Evidence-capture format

Test evidence MUST be captured in a form that is reconstructable
from repository artifacts alone (constitution Principle II and
Feature 001 FR-005). Acceptable evidence:

- **Captured test logs**: `pytest -q` output committed to the
  feature branch (or attached to the PR as a comment) and linked
  from the pre-merge attestation.
- **Captured validator output**: `python -m creator_engine_validator
  check-examples` output linked from the pre-merge attestation.
- **Coverage and lint summaries**: where applicable, captured to the
  same location.
- **Reproduction commands**: every evidence artifact MUST be paired
  with the command that produced it so a reviewer can re-run.

Unacceptable evidence:

- **"Tests pass on my machine"**: a self-claim of completion per
  constitution Principle VII; rejected by Definition of Done (FR-014).
- **Screenshot-only evidence** for surfaces that produce text
  output: the text output is canonical.
- **Stale logs**: logs from a prior commit; evidence MUST be
  recaptured for the actual commit under review.

Post-Feature-003 CI provides automated capture of the same evidence;
the manual capture remains acceptable for substrate-development work
that runs offline.

## f. "Agent says it works" rejection invariant (Feature 001 FR-014)

A spec MUST NOT enter `done` without an attestation record
satisfying FR-004 and FR-008. Self-claims of completion ("the agent
says it works") are rejected as in-progress regardless of how
detailed the claim is.

Operating implications:

- An agent reporting "validation passed" without recorded validator
  output is in-progress, not done.
- A reviewer accepting a "trust me" claim is itself a governance
  failure regardless of the reviewer's seniority.
- The Definition of Done check is mechanical: attestation linkage
  present, mutation class matched, ratifier distinct from author,
  evidence recorded. The check does not interrogate the agent's
  narrative; it interrogates the records.
- Evidence drift between two stages — e.g., a passing pre-merge
  attestation that disagrees with a passing post-merge finalization
  — is a `semantic` conflict per the conflict taxonomy and must be
  resolved before any further downstream transition advances.

This invariant is what makes the verifies-not-ratifies boundary
durable. CI evidence, agent evidence, and human evidence are all
inputs to the attestation record; none of them is ratification.

## Acceptance posture for this document

This TESTING_STRATEGY.md satisfies Feature 002 Canonical Document
Specification #14: every required section is present; the
self-claim rejection invariant is cited (Feature 001 FR-014); the
historical Feature 003 CI execution deferral is explicit; the
testing-level-to-mutation-class table in
[`./QA_STRATEGY.md`](./QA_STRATEGY.md) §b is the authoritative
shared table, cross-referenced here.
