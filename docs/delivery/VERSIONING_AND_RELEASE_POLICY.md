# Versioning and Release Policy

Creator Engine uses public product tags for release identity and keeps internal
roadmap/gate identifiers separate from public semver.

## Public product tags

Public Creator Engine releases use semantic-version-style product tags of the
form `vMAJOR.MINOR.PATCH`.

The first public product tag direction is `v0.1.0`. No tag or GitHub release is
created by this policy document itself; tag and release publication require a
later, separate Operator-ratified publication gate after the release surfaces are
merged.

## First release package coupling

For the first public release direction, the `creator-engine-validator` package
remains version `0.1.0`. The product tag `v0.1.0` is coupled to
`creator-engine-validator` package version `0.1.0` for that first release.

This coupling records the initial public cut only. Later product tags may revise
package-version policy through a separately governed change.

## Internal gate identifiers are not semver

Creator Engine G2.* identifiers are internal roadmap, governance, and gate
tracking numbers. They are not public product versions, do not imply release
ordering, and must not be used as a substitute for public product semver tags.

## Draft v2 substrate boundary

The draft v2 specification and validator substrate are internal/draft roadmap
material. They are not a shipped v2 runtime and do not change the public release
identity of the current governed kernel.

The first public release direction is the current `origin/main` governed kernel
plus release-ready validator/package substrate, not a v2 runtime release.

## Publication authority

Creating a git tag, publishing a GitHub release, changing package versions, or
changing release credentials/settings is outside ordinary documentation work.
Those actions require a later, separate Operator-ratified publication gate with
explicit evidence, validation, and stop conditions.

## Release-publish validation

A release-publish PR is a code change, not a signature ceremony. Do not run
full local `ce validate-pr` as a standing pre-push, harvest, controller, or
merge-gate prerequisite. Push the committed current head; wait for required
Validate checks; require independent review and ratification. Verifying only
the release signature is not sufficient.

Publishing a new version `X.Y.Z` updates `docs/llms-install.md` and adds
`docs/downloads/X.Y.Z/`, which can expose stale version-pinned install-spec
tests that assert the prior version:

- `validators/tests/unit/test_v3_installer.py`
- `validators/tests/integration/test_install_bootstrap.py`
- `validators/tests/unit/test_onboard_apply_live.py`

The publish PR must update those version-pinned tests to the new version in the
same PR. The required Validate result for the exact pushed head is the
authoritative evidence that this coupling is green.

Cautionary example: a release-publish PR (0.2.0 → 0.3.0) was pushed after
verifying only the release signature. Six version-pinned install-spec
assertions still expecting `0.2.0` went RED at CI. Required current-head CI is
therefore load-bearing release evidence, not a forge-round-trip inconvenience.

The durable fix is to make those install-spec tests read the version
dynamically from `creator_engine_validator.version` (release-agnostic) so a
release bump no longer requires editing them. That refactor is tracked on the
internal roadmap under the autonomous-release work (W2 release-bump).

## Draft installer mirror backport policy

Status: Draft for Operator ratification.

This section governs changes to published installer mirror content under
`docs/downloads/<version>/`, the top-level installer entry point, and the signed
install spec that names their hashes. It exists to make the choice between
backporting into an existing mirror and preserving immutability explicit before a
security or reliability event forces an ad hoc decision.

Until ratified, this section is guidance for review and release planning. It
does not by itself authorize a mirror mutation, release publication, signing-key
use, or release deprecation.

### Scope

This policy applies when a published installer artifact, `SHA256SUMS` entry,
wheel, script, or signed install-spec pointer would change after users may have
observed or pinned the original bytes.

Editing `docs/downloads/<version>/` is a release operation. It is not ordinary
documentation work. A release operation requires explicit Operator ratification,
a release owner named in the PR or release packet, and a signer with custody of
the approved release signing key. A governed worker may prepare proposed bytes
only inside its assigned scope; it may not sign, ratify, approve, merge, or
publish the release operation.

### Decision options

#### Option A: Mutate and re-sign the existing mirror

Replace bytes under the existing `docs/downloads/<version>/` path, regenerate
`SHA256SUMS`, update every signed install-spec hash that covers the changed
content, and re-sign the install spec.

Use this option only when the existing version URL is itself the safest user
path, such as a severe bootstrap vulnerability where old one-liners or agent
instructions will keep fetching the vulnerable artifact and a new version alone
would not reach affected users fast enough.

Benefits:
- Protects users who keep installing from the existing version URL.
- Avoids leaving a known-bad bootstrap path active while waiting for users to
  notice a new point release.
- Can be the fastest mitigation for a live security exposure.

Costs:
- Breaks strict hash-pinning by consumers who recorded the original bytes.
- Makes a version URL no longer immutable, which weakens reproducibility.
- Requires a prominent audit trail so users can distinguish an authorized
  republish from mirror tampering.
- Can create two populations of the same version: users who saw the original
  bytes and users who saw the replacement bytes.

#### Option B: Keep the mirror immutable, deprecate it, and publish a point release

Leave the existing `docs/downloads/<version>/` bytes unchanged. Mark the version
deprecated in release notes or install guidance, publish a fixed point release at
a new version path, and move default installer guidance to the new release.

This is the default for post-GA and otherwise stable public versions.

Benefits:
- Preserves hash-pinning and reproducible install history.
- Keeps each version URL meaning one stable byte set.
- Gives downstream mirrors, SBOMs, and audit logs a clean upgrade boundary.
- Avoids surprising users who intentionally pin exact hashes or artifacts.

Costs:
- Users who keep installing the old version may remain exposed until they follow
  the deprecation notice.
- The project must maintain clear warning surfaces so old instructions do not
  silently remain attractive.
- Emergency response can be slower if the old installer remains a common entry
  point.

#### Option C: Hybrid deprecation with a signed revocation pointer

Keep the old mirror bytes immutable, publish a fixed point release, and add a
signed advisory, revocation marker, or installer refusal path that tells users
the old version is deprecated or blocked. This option avoids mutating the old
artifact payload while still giving the install flow a stronger warning than
release notes alone.

Use this when the old artifact can safely remain archived, but continuing to run
it without warning would be irresponsible.

Benefits:
- Preserves artifact immutability for consumers who pin historical bytes.
- Gives active installers a machine-checkable signal to stop or upgrade.
- Makes the response auditable without overloading the meaning of a version URL.

Costs:
- Requires the installer or signed spec to already support the refusal or
  advisory mechanism.
- Does not help fully offline consumers who only have the old bytes.
- Still requires a signed-release operation for the advisory or pointer.

### Recommended default

Default to Option B for any post-GA or stable public release: keep
`docs/downloads/<version>/` immutable, deprecate the affected version, and publish
a fixed point release.

Use Option C when the install path can surface a signed refusal or warning
without changing the old artifact payload.

Use Option A only by explicit Operator exception when all of the following are
true:

1. The existing mirror path creates material user risk if left unchanged.
2. A point release plus deprecation is not sufficient to reach likely affected
   users in time.
3. The PR or release packet records why immutability is being broken.
4. Before and after hashes are preserved in the audit trail.
5. The signed install spec is regenerated, re-signed, and verified before
   publication.

Pre-GA release candidates and unreleased staging mirrors may use Option A with a
lower bar, because consumers should not yet treat those bytes as durable. Even
then, any edit under `docs/downloads/<version>/` remains a release operation and
must be traceable through review, hash regeneration, and signing evidence.

### Audit trail requirements

Every mirror change or deprecation response must include:

- The selected option and the reason it was chosen.
- The affected version path and artifact names.
- Original hashes and replacement hashes when bytes change.
- The regenerated `SHA256SUMS` digest and the signed install-spec digest.
- The signing key id, signing namespace, and verification result.
- The Operator ratification record or explicit statement that ratification is
  pending.
- User-facing release notes or install guidance for any deprecated version.

For Option A, the audit trail must say plainly that a published version mirror
was intentionally republished. The PR must not describe the change as a normal
documentation edit.

### Hash-pinning expectations

Consumers may pin installer URLs, `SHA256SUMS` contents, wheel hashes, script
hashes, or the signed install-spec digest. The project should assume that
post-GA versioned mirror paths are externally observed and hash-pinned shortly
after publication.

Therefore, a hash mismatch at an existing version URL is a serious compatibility
event even when the new bytes are safer. The project should prefer a new version
path for fixed bytes, and should treat any same-version hash change as a
republish that needs release notes and signing evidence.

### Signed-release interaction

When a release operation changes mirror bytes, the release owner must:

1. Regenerate `docs/downloads/<version>/SHA256SUMS` from the final artifact
   bytes.
2. Update the signed install spec fields that name the artifact base URL,
   `SHA256SUMS` digest, installer hash entry, wheel hashes, and any other
   affected artifact hash.
3. Reconstruct the canonical install-spec bytes.
4. Sign those canonical bytes with the approved OpenSSH signing key and
   namespace.
5. Embed the new signature and canonical content digest.
6. Verify the signature with the published trust root and an independent trust
   anchor before publication.
7. Push the committed head and record the required Validate run URL/status for
   that exact head.

Changing only `SHA256SUMS` is not sufficient. The signed install spec is the
authority that binds the installer flow to the mirror bytes, so it must move in
lockstep with the mirror.

### Review checklist

Before a PR that touches a published release mirror is pushed or merged, confirm:

- The PR title and body identify it as a release operation.
- The selected option is named, with the default used unless an exception is
  justified.
- `docs/downloads/<version>/` changes are performed only by an explicitly named
  release owner under Operator ratification.
- The signer and verification evidence are present.
- User-facing guidance explains whether users should keep pinning the old
  version, move to a point release, or treat the old version as deprecated.
- The required Validate run passed for the exact pushed head (or required
  synthetic merge-group head), with its URL/status recorded.
