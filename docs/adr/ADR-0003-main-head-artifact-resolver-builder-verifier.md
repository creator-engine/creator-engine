# ADR-0003 — Ratified main-HEAD artifact resolver, builder, verifier, and promote surface

- **Status:** Proposed — awaiting Operator ratification.
- **Date:** 2026-07-02
- **Gate:** Main-HEAD artifact trust surface — docs-only ADR/design.
- **Mutation class:** docs/governance documentation only. This ADR changes no implementation code,
  release artifact, installer script, validator behavior, workflow, or download payload.
- **Authority basis:** Operator-scoped seed brief for a ratification-gated design. This proposal grants no
  implementation authority until the Operator ratifies the trust contract.

> This ADR **proposes** a new trust surface for `origin/main` HEAD artifacts. It is not accepted yet,
> does not authorize implementation, and must be treated as **ratification-gated**.

---

## 1. Context

Creator Engine's stable install and update chain is release-oriented and signed:

- `docs/install.sh` fetches `docs/llms-install.md` and `docs/keys/ce-root-v1`, verifies the signed
  install spec with stock `ssh-keygen`, checks `SHA256SUMS`, installs from a verified offline wheelhouse,
  and atomically promotes the bootstrap venv.
- Versioned mirrors under `docs/downloads/<version>/` carry release-local `install.sh`, `SHA256SUMS`,
  and wheel artifacts; `validators/creator_engine_validator/checks/release_artifact_parity_guard.py`
  keeps the served installer, mirrored installer, and release checksum entry bound.
- `validators/creator_engine_validator/update.py` implements the signed in-place `ce update` path:
  signed install-spec verification, DNS-pinned `ce-root-v1` trust-anchor evidence, `SHA256SUMS`
  verification, wheel identity checks, and atomic venv promotion with `install-state`.
- `validators/creator_engine_validator/release_publish.py` stages deterministic signed-release payloads
  with a placeholder signature and an Operator signing command; `release_orchestrate.py`,
  `release_bump.py`, and `release_changelog.py` compose the release staging packet without signing or
  publishing. `validators/creator_engine_validator/packaging_runtime.py`,
  `wheel_bake.py`, and `wheel_source_parity.py` define and verify the first-party packaging contract.

That chain is correct for public releases. It does not, by itself, define authority for a contributor or
operator lane that wants current `origin/main` HEAD before the next signed release. A main-HEAD artifact
has no `ce-root-v1` release signature and must not pretend to have one. The existing CLI surface already
distinguishes the intended track in `validators/creator_engine_validator/ce_cli.py` (`ce update --track
main`) and the current main-HEAD runtime surface is separated in
`validators/creator_engine_validator/main_head_install.py`; this ADR supplies the ratification contract
that such a surface must satisfy before it is trusted as a governed install/update path.

## 2. Decision Proposal

### D1 — Main-HEAD is a separate trust chain, not an unsigned release

The main-HEAD path MUST be separate from the signed-release chain. It MUST NOT reuse `ce-root-v1`
release-signature language, placeholder signatures, release `SHA256SUMS`, or the public mirror as if a
main-HEAD artifact were a release. The trust model is:

1. Resolve a named source ref (`origin/main`) to an exact commit SHA.
2. Build first-party artifacts locally from that exact commit.
3. Verify source and artifact hashes fail-closed.
4. Promote only a verified local venv target, with a durable verification and rollback record.

The signed-release chain remains the default for `ce update --track release` and initial public install.
The main-HEAD chain is an explicitly selected development/operator track.

### D2 — Required four-step contract

**1. Fetch/resolve.** The resolver MUST fetch `origin main` and resolve `refs/remotes/origin/main^{commit}`
to exactly one 40-hex commit SHA. It MUST fail closed on network error, missing `git`, non-git checkout,
ambiguous ref, detached local guesswork, remote/branch values other than `origin/main`, or a non-commit
object. The verification record MUST include `remote`, `branch`, `source_commit`, and a source archive
hash such as `git archive --format=tar <source_commit>` SHA-256.

**2. Build.** The builder MUST materialize a detached worktree at the resolved commit, verify that the
worktree HEAD equals the resolved SHA, embed that commit SHA into the first-party package identity, and
build the `creator-engine-validator` wheel from source using the existing packaging contract. The build
MUST be reproducible in the CE sense: same resolved commit, packaging inputs, dependency wheelhouse, and
build recipe yield the same first-party artifact record. The record MUST include package version,
wheel filename, wheel SHA-256, embedded build commit, build-source hash, dependency wheel names and
hashes, and the build tool/runtime versions needed for later diagnosis.

**3. Verify.** Verification MUST be fail-closed and hash-based. The verifier MUST check that the source
archive hash has not changed between resolve and build, that the materialized source tree matches the
resolved commit, that the built wheel reports the same source commit, that the wheel bytes hash to the
builder-reported digest, that dependency wheels hash to the recorded values, and that the artifact
manifest hash is non-self-referential. There is no trust-on-first-use, no placeholder signing, and no
warning-only mismatch. The durable verification record MUST include:

- `kind: ce-main-head-artifact`
- `schema_version`
- `track: main`
- `remote`, `branch`, `source_commit`
- source archive SHA-256 and build-source SHA-256
- package name/version
- app wheel filename/SHA-256
- dependency wheel filenames/SHA-256 values
- artifact-manifest SHA-256
- verification rows with expected/actual SHA-256 and `ok`
- `trust_model: verified-source-build-main-head`
- `signature: none`
- timestamp and installing runtime identity

**4. Install/promote.** The installer MUST build or reuse a versioned venv target named by the resolved
commit and artifact-manifest hash, install only from the verified local wheelhouse with `--no-index`, and
verify the `ce` and `cev3` entrypoints before promotion. Promotion MUST be atomic at the `install_root/venv`
pointer level. If promotion or state writing fails, the previous live venv pointer or directory MUST be
restored before returning failure. The installer MUST write both a durable artifact manifest and
`install-state` that records `install_kind=main-head`, the source commit, source/build hashes, wheel hash,
artifact manifest path, trust model, and live/target venv paths.

## 3. Trust Anchor Options

### Option A — Commit-SHA pinning plus local reproducible build

This option treats the exact resolved `origin/main` commit SHA as the trust anchor for the unsigned track.
The installer trusts only artifacts built locally from that exact SHA and only after source and wheel hashes
match the verification record.

**Pros:** minimal new infrastructure, composes with current local source-build code, avoids pretending the
artifact is signed, gives deterministic rollback records, and blocks ref drift after resolve.

**Cons:** it anchors to the forge ref resolution and repository history controls. It does not add an
independent CI witness and does not protect against an already-compromised `origin/main`.

### Option B — CI artifact attestation

This option requires CI to build or attest the main-HEAD artifact, and the installer verifies the attestation
before promotion.

**Pros:** adds an independent build witness and can later align with SLSA/provenance controls.

**Cons:** requires a ratified attestation issuer, verifier, retention model, and failure policy. Until those
are ratified, it risks replacing a simple SHA pin with an underspecified CI trust root.

### Option C — Operator-signed interim certificates

This option has the Operator sign interim main-HEAD artifact certificates outside the release chain.

**Pros:** strongest human-rooted authority for exceptional installs and close to release semantics.

**Cons:** operationally heavy for fast `main` tracking, risks confusing interim certificates with
`ce-root-v1` releases, and can become a parallel release process unless tightly governed.

**Recommended default:** Option A. Commit-SHA pinning plus local reproducible build is the interim default
for `--track main` because it is honest about the unsigned trust boundary and can be made fail-closed with
the current packaging/install primitives. Option B should be the next ratified hardening layer for remote
or fleet-wide main-HEAD artifacts. Option C should remain reserved for exceptional Operator-directed
promotion where a human ratification gesture is intentionally required.

## 4. Composition with `ce update`

`ce update` has two explicit tracks:

- `ce update --track release` uses `validators/creator_engine_validator/update.py` and remains the signed
  release/mirror path.
- `ce update --track main` layers on top of this ADR's main-HEAD contract. It MUST behave like
  `clean-main-install` with update ergonomics: resolve, build, verify, and optionally promote the exact
  current `origin/main` commit. `--check` MUST run through resolve/build/verify without changing the live
  install root.

The two tracks may share helper concepts such as install roots, venv promotion, entrypoint verification,
and `install-state` shape. They MUST NOT share trust assertions that would imply main-HEAD artifacts are
release signed.

## 5. Failure and Rollback Semantics

All main-HEAD phases fail closed:

- Fetch/resolve failure leaves the current install untouched.
- Source mismatch, worktree mismatch, build mismatch, wheel mismatch, dependency mismatch, manifest mismatch,
  or entrypoint failure leaves the current install untouched.
- Promotion failure restores the prior live venv pointer or directory when possible and records enough
  failure context for diagnosis.
- A successful promotion writes a rollback-capable record naming the previous live state when available,
  the new target, and the artifact manifest used for promotion.
- A failed `--check` returns refusal evidence but performs no persistent mutation.

No phase may downgrade a hard mismatch into a warning, and no phase may proceed by fetching unpinned or
network-resolved dependencies during install.

## 6. Operator-Ratified vs Automatic

**Must remain Operator-ratified:**

- Acceptance of this main-HEAD trust model.
- Any change from commit-SHA pinning to CI attestation as a required trust anchor.
- Any use of Operator-signed interim certificates.
- Any permission to consume prebuilt remote main-HEAD wheels.
- Any broadening beyond `origin/main`.
- Any weakening of fail-closed hash, source, entrypoint, or rollback checks.
- Any merger of this trust chain into the `ce-root-v1` signed-release chain.

**May be automatic after ratification:**

- Resolving the latest `origin/main` commit.
- Building the first-party wheel from that exact commit.
- Computing and recording source, wheel, dependency, and manifest hashes.
- Running `--check` verification.
- Promoting the verified venv target for an explicitly selected `--track main` invocation.
- Reusing a previously verified target whose commit and artifact-manifest hash exactly match the record.

## 7. Consequences

- Contributor lanes such as clean-main install and auto-track-main get a concrete ratification target without
  waiting for the next signed release.
- Public release installs keep their stronger signed mirror chain and remain the default.
- Main-HEAD installs are auditable as unsigned, locally built, SHA-pinned artifacts rather than disguised
  releases.
- Future CI attestation can compose with this ADR by adding an attestation row to the verification record
  without removing commit-SHA pinning.

## 8. References

- `docs/install.sh`
- `docs/downloads/0.3.1/install.sh`
- `docs/downloads/0.3.1/SHA256SUMS`
- `docs/llms-install.md`
- `docs/keys/ce-root-v1`
- `validators/creator_engine_validator/ce_cli.py`
- `validators/creator_engine_validator/update.py`
- `validators/creator_engine_validator/main_head_install.py`
- `validators/creator_engine_validator/release_publish.py`
- `validators/creator_engine_validator/release_orchestrate.py`
- `validators/creator_engine_validator/release_bump.py`
- `validators/creator_engine_validator/release_changelog.py`
- `validators/creator_engine_validator/packaging_runtime.py`
- `validators/creator_engine_validator/wheel_bake.py`
- `validators/creator_engine_validator/wheel_source_parity.py`
- `validators/creator_engine_validator/checks/release_artifact_parity_guard.py`
