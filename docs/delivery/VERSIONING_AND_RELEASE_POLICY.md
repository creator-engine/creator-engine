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
