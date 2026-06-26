# Changelog

All notable release-surface changes for Creator Engine are recorded here.
This file follows the public product-tag direction; internal Creator Engine
G2.* gate identifiers remain roadmap/governance work IDs, not public semver.

## [Unreleased]

(nothing yet — use this section for features landing after 0.2.0 while waiting for the next tag)

## v0.2.0 — self-hosting milestone (2026-06-25)

### Added

- Governed Worker tier: in-process sub-agent roles (architect_research, implementer, reviewer, verification)
- `ce worker run --role <role>` — governed worker launch-and-collect
- Approval wall with OpenBao credential backing — merges require a capability token
- Cross-repo ce-ops issue auto-close bot (merge-triggered)
- Host-persistent contained-seat logging (logs survive container teardown)
- Herdr authenticated reach plane — Operator can attach to contained seats without sudo docker exec
- Operator steer lock — serializes Operator input vs autonomous gate dispatch
- Belt autonomous conveyor: stranded-PR sweep + lane-pickup daemon
- `ce fleet status` — aggregated fleet observability view
- `ce seats ls` — seat liveness read-model
- Contained-seat self-push and self-review via injected credential (transport-deputy pattern)
- Merge-queue dequeue primitive + integrator settle window
- Credential-wall approval gate (approval requires a capability forks/seats lack)
- Auto-carrier generation: `ce carrier` generates and self-verifies carriers
- Release-artifact parity CI guard (served install.sh hash == published SHA256SUMS)
- Cross-repo PR closes-linkage guard validator

### Changed

- Work classes reframed as CE ceremony tiers (not Agile work items)
- foreman/swarm canon enforced deterministically at governance layer (not prompt-hope)
- Codex Ring-0 tokenless contained launch: credentials NEVER enter container env/metadata

### Fixed

- Lane harness-matrix row restored after regression
- Integrator reads latestOpinionatedReviews (gate approval count correct)
- Verify-by-reaction dispatch confirmation hardened

### Security

- Contained-seat launch fails closed if gVisor containment proof is missing (probed containment)
- Egress fail-closed confinement for contained seats
- Per-dev forge App credential isolation (CDX-D-9 clause)

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
