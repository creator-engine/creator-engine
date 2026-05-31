# Changelog

All notable release-surface changes for Creator Engine are recorded here.
This file follows the public product-tag direction; internal Creator Engine
G2.* gate identifiers remain roadmap/governance work IDs, not public semver.

## v0.1.0 — first public product tag direction

Status: planned / not yet published.

`v0.1.0` is the first public product tag direction for Creator Engine. It is
intended to package the current governed kernel and release-ready validator /
package substrate from `origin/main` after the release-surface work merges and a
separate Operator-ratified publication gate authorizes tag and release creation.

This planned first release keeps `creator-engine-validator` at package version
`0.1.0`; the first product tag `v0.1.0` is coupled to that validator package
version for the initial public cut.

Included direction:

- governed Creator Engine kernel and documentation currently landed on `main`;
- `creator-engine-validator` package substrate at `0.1.0`;
- public release policy, changelog, README release pointer, and pre-1.0 security
  support wording.

Not included as shipped runtime:

- draft v2 specification and validator substrate, which remain internal/draft
  roadmap material;
- G2.* roadmap/gate identifiers as product versions;
- tag publication or GitHub release publication before a later, separate
  Operator-ratified publication gate.
