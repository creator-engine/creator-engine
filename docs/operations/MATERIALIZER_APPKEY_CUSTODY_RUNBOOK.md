# Materializer App-Key Custody Runbook

## Status: Future Governed Procedure Only

This document records a future procedure; it is not an operating runbook.
`ARMING_ENABLED=False`: materializer signing and pushing are not live, and this
document does not authorize arming, signing, pushing, releasing, or any
credential action. No step below may be executed unless an Operator has first
ratified the applicable change and accepted the associated credential-custody
authority.

The currently landed materializer work is pre-arming and dry-run only. The
#958 pre-arming slice retains the disabled arming guard, and the #959 deploy
unit is a dry-run unit that refuses attempts to enable arming. Neither slice
installs a live signing or push procedure.

## Present Boundary

No vault-path behavior is implemented or asserted by this runbook. In
particular, it does not specify a secret-store location, lookup mechanism,
delivery channel, retention behavior, rotation mechanism, or recovery action.
It also does not grant any role access to materializer key material or a
reference that resolves to it.

The landed dry-run boundary permits only governed planning and validation. It
does not create a live materializer credential, an active signer, or a release
path. Any statement elsewhere that suggests otherwise must be treated as a
future prerequisite, not as current enforcement.

## Future Prerequisites

Before any future arming proposal can be considered, an Operator must ratify a
separate, implemented design that defines and verifies all of the following:

- Credential custody and narrowly scoped authority, without exposing material
  to workers, tracked files, prompts, logs, command arguments, or evidence.
- A reviewed delivery and rotation design with explicit failure handling and
  audit evidence.
- A tested authorization boundary for signing and pushing, including a
  fail-closed disabled state.
- The deployment, recovery, and multi-host ownership model appropriate to the
  ratified topology.

These are future requirements only. This runbook does not claim that any of
them is implemented, deployed, configured, or enforced.

## Future Rotation, Recovery, and Incident Prerequisites

While `ARMING_ENABLED=False`, rotation, recovery, revocation, and incident
response remain future-only procedures and are not available. Before a future
Operator-ratified arming proposal, Operator custody must ratify documented
evidence for replacement, recovery, immediate revocation, incident escalation,
and audit handling. A future procedure must fail closed--leaving arming,
signing, pushing, and release disabled--whenever that ratification or its
required evidence is absent. This records no current rotation, recovery,
revocation, or incident-response enforcement.

## Future Per-Call Signing Boundary

While `ARMING_ENABLED=False`, no signing boundary is live. Any future
Operator-ratified design must require a separately authorized per-call signing
operation, with no reusable credential material exposed to workers, tracked
files, prompts, logs, command arguments, or evidence. Absent the ratified
design and its evidence, the future design must fail closed with signing,
pushing, and release disabled. This runbook neither configures nor asserts a
current signer or signing integration.

## Future Single-Host Lease and Topology Prerequisite

While `ARMING_ENABLED=False`, no materializer lease is live. Any future
Operator-ratified deployment must establish a single-host lease constraint and
fail closed when its ownership evidence is absent or contested. Before any
future multi-host use, an Operator must reconsider and ratify the topology,
ownership, recovery, and lease model; no multi-host use is authorized by this
runbook. This is a future prerequisite, not current lease or topology
enforcement.

## Roles and Non-Authorities

Only a future ratified Operator procedure may assign custody or recovery
authority. Worker roles, including implementers and reviewers, have no
credential-custody, arming, signing, push, release, or break-glass authority.
The materializer remains dry-run only while `ARMING_ENABLED=False`.

## Review Boundary

Any proposal to replace this future-only document requires a separately
reviewed implementation and explicit Operator ratification. Until then, use
the landed #958/#959 dry-run and pre-arming behavior as the sole current
materializer boundary.
