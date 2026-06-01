# ADR-V2-006-3: read-only tracker connector (Jira + GitLab) (`ce connector`)

## Status

Accepted for G2.005.3 draft runtime.

## Context

The merged connector runtime is GitHub-only: G2.005.1 (read) and G2.005.2 (strict-mode
write) both target a GitHub source host. The read plan, the injectable client seam, and
the redaction-safe receipt are already provider-agnostic, but the only adapters are
GitHub. G2.005.3 generalizes the **read** path to additional providers without breaking
the repo's offline testing discipline or the substrate's vendor-neutral descriptor
contract.

## Decision

G2.005.3 adds read-only **Jira** and **GitLab** (REST) adapters over the same seam, a
`PROVIDER_READ_CLIENTS` registry, and provider selection in `fetch`; `ce connector
fetch` gains a `--provider {github,jira,gitlab}` flag (default `github`). It reuses the
G2.005.0 validator, changes no GitHub read/write behavior, and imports no
CE-event/PCL/distributed-identity code.

Key boundary decisions:

- **Read-only only.** Tracker adapters expose GET only; a `write` scope / non-read verb
  is refused before any request (`G2-CONN-WRITE-REFUSED`/`G2-CONN-SCOPE`) for every
  provider. The tracker **write** runtime (`tracker_mirror` writes for Jira/GitLab) is a
  deferred follow-up.
- **Providers = Jira + GitLab (REST); Linear deferred.** Jira and GitLab map onto the
  existing resource-path read seam. Linear is GraphQL (single POST endpoint + query
  document) and does not fit the resource-path model; it is an explicit, named deferral
  to a later slice that generalizes the seam for GraphQL — not an omission of the
  dev-map line.
- **Provider selected by a runtime `--provider` flag (default `github`).** The
  substrate declares `provider_class` "an opaque label, never a concrete vendor binding
  as normative," and the connector object is `additionalProperties: false`. The
  descriptor therefore stays vendor-neutral and the concrete adapter is bound at
  invocation; no descriptor `provider` field is added and no schema is touched.
  `default github` reproduces the G2.005.1 behavior exactly, so all existing tests
  remain green canaries. Descriptor-bound provider selection (a schema change) is a
  separate, deferred gate.
- **Provider-correct auth by reference.** GitHub and Jira use a `Bearer` header; GitLab
  uses its native `PRIVATE-TOKEN` header — each derived from the credential resolved BY
  REFERENCE and never stored, printed, logged, or committed.
- **Network only through an injectable seam.** Each default adapter reaches the network
  only via the injectable opener, so tests inject a fake and the suite/`check` make no
  real request; an unknown provider fails closed (`G2-CONN-PROVIDER`) and any transport
  error fails closed (`G2-CONN-NETWORK`). Request construction and response parsing are
  unit-tested; only the literal socket call is unexercised.

## Consequences

- The connector read runtime is multi-provider and offline-testable, with the read-only
  floor, the credential-by-reference boundary, and the vendor-neutral descriptor
  contract preserved across providers, on a stable seam.
- Later gates can add Linear/GraphQL (generalizing the seam) and the tracker write
  runtime on the now-proven provider registry, each under its own ratification.

## Non-ratification statement

This ADR records a design decision for the PR candidate. It ratifies no tracker write
authority, no Linear/GraphQL surface, no credential storage/brokering, no descriptor
schema change, and no agent ratification.
