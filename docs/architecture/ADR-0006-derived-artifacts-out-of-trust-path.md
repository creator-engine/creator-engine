---
kind: decision-record
record_type: adr
schema_version: "1"
id: ADR-0006-derived-artifacts-out-of-trust-path
title: "Derived Artifacts Out Of The Trust Path"
status: accepted
date: "2026-06-19"
decision_makers: [dev-3]
consulted: [ce-ops#133, ce-ops#91, ce-ops#65]
informed: []
review_by: "2026-09-19"
mutation_class: docs
evidence_refs:
  - kind: issue
    ref: "https://github.com/creator-engine/ce-ops/issues/133"
    tag: ce-ops-133
  - kind: issue
    ref: "https://github.com/creator-engine/ce-ops/issues/91"
    tag: ce-ops-91
  - kind: issue
    ref: "https://github.com/creator-engine/ce-ops/issues/65"
    tag: ce-ops-65
  - kind: pr
    ref: "https://github.com/creator-engine/creator-engine/pull/271"
    tag: pr-271
  - kind: doc
    ref: "validators/tests/unit/test_packaging_contract.py"
    tag: packaging-contract
  - kind: doc
    ref: "validators/tests/unit/test_wheelhouse_built_surface.py"
    tag: wheel-source-guard
  - kind: doc
    ref: "docs/devops/CI_CD_STRATEGY.md"
    tag: ci-strategy
  - kind: doc
    ref: "docs/product/REQUIREMENTS.md"
    tag: offline-requirement
crosswalk:
  informs:
    - ce-ops#133
    - ce-ops#91
    - ce-ops#65
ratification:
  ratified_by: chmod735
  ratified_at: "2026-06-19"
  ratification_prompt_sha: bb69016797062f5b53f3f5a79164f495b59c885d19172828b87a1407904d9366
---

# Derived Artifacts Out Of The Trust Path

## Ratification

The Operator ratified this ADR on 2026-06-19 as Gate-1 design acceptance.
Gates 2-3 remain separate future ratified gates. This record remains
design-only and does not authorize code, workflow, trust-root, or release
artifact changes.

## Context and Problem Statement

CE currently commits the built `creator_engine_validator` application wheel under
`validators/wheelhouse/` and treats it as part of normal source PRs. The
packaging contract correctly catches wheel/source drift ([packaging-contract],
[wheel-source-guard]), but the operational consequence is costly: any PR that
changes packaged source must also rebuild the app wheel and refresh
`validators/wheelhouse/SHA256SUMS`. PR271 exposed the same pattern from the
other side: a source-only surface that depends on packaged code must either
avoid wheel drift or pay the wheel rebuild tax even though the wheel is a
derived artifact, not authored source ([pr-271]).

That coupling places a derived binary in the merge trust path. It also creates
recurring merge conflicts, path-manifest widening, large binary diffs, and
source-review noise. Worse, it tempts reviewers to treat a rebuilt wheel as
authority rather than as evidence that source can be reproducibly built.

This accepted ADR decides the target architecture only. It does not authorize
removing the committed wheel, changing install trust roots, editing workflows,
or altering branch protection. Those are future implementation gates that
require separate Operator ratification.

## Decision Drivers

- Source review should review source, tests, schemas, docs, and lockfiles; built
  application wheels should be regenerated and verified mechanically.
- A source PR must not go green if the release wheel that CI would build from it
  differs from the source under review.
- Offline install remains mandatory: CE must still run from a fresh clone or
  signed release artifacts without reaching PyPI during normal validation
  ([offline-requirement]).
- Dependency supply must remain reproducible and hash-pinned across x86_64 and
  arm64 Linux.
- CI verifies but does not ratify; release signing and trust-root changes remain
  human/Operator events ([ci-strategy]).
- ce-ops#91 doc-currency means docs that describe install, packaging, release,
  and trust paths must stay synchronized with the implemented gates, not lag as
  aspirational prose ([ce-ops-91]).
- ce-ops#65 changelog-gate means every change that moves this contract must
  carry an auditable changelog fragment; implementation phases cannot silently
  change release semantics without user-visible release notes ([ce-ops-65]).

## Considered Options

1. **Keep committing the app wheel in every source-changing PR.**
   This keeps current offline clone installs simple, but preserves the binary
   merge conflicts, rebuild tax, and stale-wheel failure mode.
2. **Delete all wheelhouses and fetch everything from public package indexes.**
   This removes binary diffs but violates CE's offline and hash-pinned install
   posture.
3. **Un-commit only the CE app wheel, build it in CI, and publish it as a signed
   release artifact while keeping vendored runtime dependency wheels
   reproducible.**
   This removes the derived first-party binary from ordinary source PRs while
   retaining offline dependency closure and a signed release surface.
4. **Commit a generated source archive instead of a wheel.**
   This changes artifact format but does not remove the derived-artifact review
   problem.

## Decision Outcome

Chosen option: **Option 3 — un-commit the CE app wheel, build it in CI as a
signed release artifact, keep vendored dependencies reproducible, and require
merge-queue wheel/source verification.**

The accepted target state has three separated artifact classes:

1. **Authored source and policy artifacts in git.**
   Python source, schemas, tests, docs, lockfiles, release metadata, and
   dependency manifests remain in the repository and are reviewed normally.
2. **Vendored third-party dependency wheels in the repo, or an equivalent
   reproducible dependency bundle.**
   The dependency closure remains hash-pinned, cp314-only, and dual-arch where
   required. If dependency wheels later move out of git, that move needs its own
   ratified gate with the same offline and hash-pin guarantees.
3. **First-party CE app wheel as a CI-built release artifact.**
   CI builds `creator_engine_validator-<version>-py3-none-any.whl` from the
   merge candidate source, verifies it against that source, emits provenance and
   digest metadata, and publishes it only through a signed release path.

This ends the per-PR app-wheel rebuild tax. A PR that edits packaged source no
longer modifies `validators/wheelhouse/creator_engine_validator-*.whl` or the
app-wheel line in `validators/wheelhouse/SHA256SUMS`; instead, the merge queue
builds the wheel from the candidate tree and proves it matches that tree before
merge. The release pipeline, not every source PR, owns app-wheel publication.

## Required Gates

### Gate 1 — Trust-path split design acceptance

- Ratify this ADR or its successor.
- Decide the exact artifact boundary:
  - first-party app wheel leaves git;
  - third-party dependency wheelhouse stays committed initially;
  - signed release artifacts become the install authority for the CE app wheel.
- Record ce-ops#91 doc-currency obligations and ce-ops#65 changelog obligations
  in the implementation mandate.

Exit evidence:

- Accepted ADR with human ratification.
- Implementation issue links each doc that must change before the gate can
  merge.
- No code or workflow changes in this design gate.

### Gate 2 — CI build and provenance lane

- Add a CI job that builds the CE app wheel from the exact merge candidate.
- Run the existing source/wheel parity checks against the CI-built wheel rather
  than a committed app wheel.
- Emit a build manifest containing:
  - source commit SHA;
  - pyproject version;
  - wheel filename;
  - wheel sha256;
  - Python/build backend versions;
  - dependency-lock digest;
  - build command;
  - artifact attestation reference, once enabled.

Exit evidence:

- Merge-queue run exposes the app-wheel digest for the candidate commit.
- A source change that is not reflected in the candidate wheel fails CI.
- A modified local wheel cannot make CI pass because CI ignores committed
  first-party wheel bytes.

### Gate 3 — Remove committed first-party app wheel

- Delete `validators/wheelhouse/creator_engine_validator-*.whl`.
- Remove the app-wheel line from the development `validators/wheelhouse/SHA256SUMS`
  or split it into a release-only manifest.
- Keep third-party dependency wheels and their checksums intact.
- Update packaging tests so:
  - dependency-wheel posture still validates locally;
  - first-party wheel/source parity uses a built wheel from a temp build dir or
    CI artifact;
  - no test requires a committed first-party app wheel.

Exit evidence:

- Full offline tests pass on a clean clone.
- Path manifest for the implementation PR shows no replacement app-wheel binary.
- `ce doctor` reports dependency bundle posture separately from first-party
  release-wheel posture.

### Gate 4 — Signed release artifact publication

- Publish the CI-built app wheel as a release artifact only after merge and
  Operator-controlled release authorization.
- Sign the release manifest or artifact digest under the release signing policy.
- Update the install path so the trusted release manifest points to the signed
  app wheel artifact instead of an in-repo first-party wheel.
- Keep CI evidence as verification evidence, not ratification ([ci-strategy]).

Exit evidence:

- Release manifest verifies the wheel digest and source commit.
- Fresh install obtains the CE app wheel from the signed release artifact path.
- No source PR can change the public install wheel without the release gate.

### Gate 5 — Merge-queue enforcement

- Mark the CI-built-wheel parity job as required on merge queue.
- Require the dependency reproducibility job on merge queue.
- Require path-manifest fidelity and changelog-gate checks in the same queue.
- Reject merge if docs that describe install/release trust paths are stale under
  the ce-ops#91 doc-currency rule.

Exit evidence:

- A PR changing packaged source but omitting any wheel artifact passes when CI
  builds and verifies the wheel.
- A PR that edits install/release behavior without the required docs and
  changelog fails.
- A PR that tampers with dependency lockfiles or vendored dependency wheels
  without regenerated hashes fails.

## Reproducible Vendored Dependencies

The dependency closure remains a trust input even after the first-party app
wheel leaves git. The implementation must preserve:

- `validators/pyproject.toml` as the package metadata source.
- `validators/uv.lock` as the primary dependency lock.
- `validators/requirements.txt` as the lockstep export.
- `validators/wheelhouse/` or its successor as the offline dependency bundle.
- `validators/wheelhouse/SHA256SUMS` as the local digest manifest for vendored
  dependencies.
- cp314-only runtime ABI posture unless a later ADR changes the interpreter
  target.
- dual-arch Linux coverage for native runtime dependencies.

The build job should derive dependencies from the lockfile, install only from
the vendored dependency bundle, and fail if the lockfile, requirements export,
and wheel bundle disagree. Public index access is not part of the merge-queue
verification path.

## Merge-Queue Verification

The merge queue must verify the candidate tree, not the author's workstation
artifact. Required checks:

- Build first-party app wheel from `HEAD` in an isolated CI environment.
- Compare wheel package contents to source for all packaged modules.
- Verify console scripts and generated version surfaces against source.
- Verify no committed first-party app wheel exists once Gate 3 lands.
- Verify vendored dependency wheels match the dependency lock and checksum
  manifest.
- Verify path manifest equals `base..HEAD`.
- Verify changelog fragment exists for any implementation gate that changes
  install, packaging, release, CI, or trust-path behavior.
- Verify docs touched by ce-ops#91 are current when install/release behavior
  changes.

This makes wheel/source drift impossible to merge: the only wheel that matters
for the check is built from the exact source being merged, and the source tree is
the merge queue candidate.

## ce-ops#91 Doc-Currency Touchpoints

Every implementation gate must update or explicitly attest no-change for:

- `docs/llms-install.md`
- `docs/operations/AGENT_NATIVE_BOOTSTRAP.md`
- `docs/operations/V1_DELIVERY_REHEARSAL.md`
- `docs/devops/CI_CD_STRATEGY.md`
- `docs/product/REQUIREMENTS.md`
- `validators/README.md`
- any release runbook or install contract introduced before the gate lands

The ADR's target state is not complete while docs still say the CE app wheel is
installed from a committed in-repo first-party wheel. Gate 3 and Gate 4 must
make the docs and implementation agree in the same PR or fail the doc-currency
gate.

## ce-ops#65 Changelog-Gate Touchpoints

Each phase must include a changelog fragment when it changes any of:

- source/release artifact boundaries;
- install source of the app wheel;
- dependency vendoring posture;
- CI/merge-queue requirements;
- packaging-contract test meaning;
- signed release manifest contents.

The changelog should name whether the change is design-only, CI-only,
install-path affecting, or release-path affecting. This keeps external users
from learning about trust-path changes only by reading test failures or PR
manifests.

## Risks And Mitigations

- **Risk: offline clone installs regress.**
  Mitigation: keep vendored dependencies in repo at first; provide a local
  `python -m build` path for the app wheel; require full offline install tests
  before deleting any current install path.
- **Risk: release artifact signing becomes the new bottleneck.**
  Mitigation: CI emits unsigned verification artifacts for every merge
  candidate, but only release gates request signing. Source PRs stop needing
  release signatures.
- **Risk: CI-built wheels are not reproducible across environments.**
  Mitigation: pin Python, build backend, dependency lock, and build command;
  record the build manifest; fail if local reproduction cannot match the CI
  digest once reproducible-build enforcement is enabled.
- **Risk: vendored dependency bundles become stale.**
  Mitigation: keep lockfile/export/wheelhouse checksum checks required, and
  treat dependency refreshes as explicit packaging changes with changelog and
  manifest entries.
- **Risk: users confuse CI artifacts with ratified releases.**
  Mitigation: CI artifacts are verification evidence only; signed release
  manifests are the install authority.
- **Risk: implementation widens beyond design.**
  Mitigation: each gate has an explicit exit condition and remains blocked
  until Operator ratification authorizes code, workflow, or trust-root changes.

## Consequences

- Good: ordinary source PRs no longer carry the first-party app wheel binary or
  update its checksum line.
- Good: merge conflicts on the app wheel disappear.
- Good: wheel/source drift becomes structurally unmergeable because the merge
  queue builds the wheel from the merge candidate.
- Good: release artifacts become auditable outputs with digest/provenance
  records instead of opaque blobs inside source PRs.
- Good: docs and changelog gates become explicit parts of trust-path changes.
- Bad: CI and release automation become more important and must be reliable.
- Bad: fresh clone install behavior needs a careful migration path so offline
  guarantees are not weakened.
- Bad: until Gate 4 lands, CE has two concepts to explain: CI verification
  artifacts and signed release artifacts.
- Bad: reproducible-build rigor may expose nondeterminism in generated metadata
  that current committed-wheel workflows hide.

## Gate Boundary Statement

This accepted ADR records Gate-1 design acceptance only. It does not remove any
wheel from git, change install scripts, change signed manifests, publish release
artifacts, alter CI workflows, or change branch protection. Any binding
implementation requires a later ratified gate.
