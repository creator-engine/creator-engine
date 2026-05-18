# External Contributor Intake Boundary

## Purpose

This note fixes the governance boundary for external contributions during
the v0.1 governance substrate. It defines how pull requests opened by
parties outside the implementer-pane authorship circle are received,
evaluated, and (when appropriate) ratified, without enlarging the
project's public surface area or weakening the Source ratification
guarantee.

## Scope

In scope:

- The boundary contract between external contributors and the governance
  substrate.
- The respective roles of issues, envelopes, pull requests, and CI in
  that contract.
- The ratification gate that privileged surfaces continue to require.

Out of scope:

- Any public visibility change to the repository or its artifacts.
  Public visibility, discoverability, and broader OSS-readiness remain
  out of scope until a later, explicitly gated work stream addresses
  them.
- Any change to identity, attestation, redaction, deploy/release, or
  CODEOWNERS surfaces.

## Boundary statement

External pull requests are treated as proposals from authors who sit
outside the implementer-pane authorship circle. They do not inherit
implementer-pane authority by virtue of having opened a PR, and CI
acceptance does not promote them across the boundary.

## Channel semantics

Each channel carries exactly one kind of payload across the boundary,
and only that kind:

- **Issues carry information.** They describe a problem, a request, or
  an observation. They do not, on their own, authorize any change.
- **Envelopes carry authority.** A governance envelope is the only
  mechanism by which a decision, scope, or ratification is conveyed.
  Authority does not leak from issues or PRs; it travels only in
  envelopes.
- **Pull requests carry change.** A PR is a proposed diff against the
  repository. It is the unit of change under review; it is not the
  unit of authority.
- **CI verifies but never ratifies.** Continuous integration confirms
  that a proposed change satisfies mechanical checks (build, lint,
  schema validation, tests). A green CI run is necessary evidence but
  is not, and must not be treated as, ratification. CI cannot stand in
  for a Source decision.

## Ratification gate for privileged surfaces

Privileged surfaces — including but not limited to governance schemas,
validators, examples, templates, tenants, specs, identity, attestation,
redaction, deploy/release, and surfaces designated by the authority and
mutation-class models — require explicit Source ratification before
merge. An external PR touching such a surface must receive a ratifying
envelope from Source; without it, the change is not eligible for merge
regardless of CI status, reviewer comments, or contributor seniority.

This rule is symmetrical: implementer-pane authors are also bound by
Source ratification on privileged surfaces. The external-contributor
boundary does not weaken the gate; it makes the gate's role explicit
for parties who do not already operate inside the implementer pane.

## Visibility posture

Treating external PRs as governed input does not imply that the
repository, its issues, or its CI surfaces are publicly visible.
Public visibility, including any expansion of who can open issues or
PRs in the first place, remains out of scope. It will be revisited only
under a later, explicitly gated OSS-readiness work stream that addresses
discoverability, contribution policy, security disclosure, and license
posture together.

## Summary

External PRs are outside-the-pane proposals. Issues inform, envelopes
authorize, PRs change, and CI verifies. Ratification of privileged
surfaces remains a Source act, and public visibility is deferred to a
future gated effort.
