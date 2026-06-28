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

## Release-publish preflight

A release-publish PR is a code change, not a signature ceremony, and is subject
to the same mandatory preflight as any other PR: `ce validate-pr` (the full
CI-parity offline suite, whole tree, on a CLEAN working tree) MUST go green
locally before the PR is pushed. Verifying only the release signature is not
sufficient. The offline suite mirrors `.github/workflows/validate.yml`, so a
local green ≈ CI green.

Release-publish PRs have a specific failure mode that makes this preflight
non-optional. Publishing a new version `X.Y.Z` updates `docs/llms-install.md`
and adds `docs/downloads/X.Y.Z/`, which BREAKS the version-pinned install-spec
tests that assert the prior version:

- `validators/tests/unit/test_v3_installer.py`
- `validators/tests/integration/test_install_bootstrap.py`
- `validators/tests/unit/test_onboard_apply_live.py`

The publish PR MUST run `ce validate-pr` locally and update those version-pinned
tests to the new version **in the same PR** before pushing.

Cautionary example: a release-publish PR (0.2.0 → 0.3.0) was pushed after
verifying only the release signature. Six version-pinned install-spec
assertions still expecting `0.2.0` went RED at CI — every one of them would have
been caught by running the offline suite locally first.

The durable fix is to make those install-spec tests read the version
dynamically from `creator_engine_validator.version` (release-agnostic) so a
release bump no longer requires editing them. That refactor is tracked on the
internal roadmap under the autonomous-release work (W2 release-bump).
