# ADR-V2-006-1: GitHub connector read-only runtime (`ce connector`)

## Status

Accepted for G2.005.1 draft runtime.

## Context

The merged G2.005.0 connector substrate (`checks/connector_substrate.py` +
`schemas/connector.schema.yaml` + `schemas/mission-brief.schema.yaml`) defined the
connector descriptor, the Mission-Brief, and the bounded `tracker_mirror` class.
G2.005.1 makes the first connector executable as a **read-only** `ce connector`
runtime. It must talk to a source host without breaking the repo's offline,
network-free testing discipline and without ever exposing credentials.

## Decision

G2.005.1 adds `validators/creator_engine_validator/connector_runtime.py` and a
`ce connector` CLI group: `verify`, `plan`, `fetch`. It reuses the G2.005.0
validator for all shape decisions and imports no CE-event/PCL/distributed-identity
code.

Key boundary decisions:

- **Read-only only.** The runtime performs only GET reads; a `write` capability
  scope or any non-read verb is refused before any request and routed to
  `G2.005.2`. The adapter exposes no write method.
- **Credential by reference.** The credential is resolved from `credential_ref`
  (env var name) at call time, used only to construct the request Authorization
  header, and is never stored in a record, printed, logged, or committed.
  `CredentialHandle` masks its value in `repr`; `secret_manager_ref` resolution is
  deferred (fails closed).
- **Network only through an injectable seam.** The default `UrllibGitHubReadClient`
  reaches the network only via an injectable `opener` (default
  `urllib.request.urlopen`), so tests inject a fake opener and the suite/`check`
  make no real request. The default fails closed (`G2-CONN-NETWORK`) on any
  transport error or when no client is configured (`NullReadClient`). Request
  construction and response parsing are unit-tested; only the literal socket call
  is unexercised.
- **Redaction-safe receipts.** Read results are normalized to a bounded field set;
  receipts carry no credential or secret. Optional cache writes target the
  git-ignored `.ce/connector/cache/`.

It implements no connector write runtime, credential injection/brokering, tracker
connectors, CI/deploy, or autonomy activation.

## Consequences

- The first connector is executable read-only and offline-testable, with the
  credential boundary and read-only floor enforced at the runtime and reused from
  the landed substrate validator.
- Later gates can bind the write runtime (`G2.005.2`) and tracker connectors
  (`G2.005.3`) on a stable read-only runtime + client seam.

## Non-ratification statement

This ADR records a design decision for the PR candidate. It ratifies no write
authority, no credential storage/brokering, no privileged-floor relaxation, and no
agent ratification.
