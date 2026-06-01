# ADR-V2-006-2: GitHub connector write runtime, strict mode (`ce connector`)

## Status

Accepted for G2.005.2 draft runtime.

## Context

The merged G2.005.0 connector substrate bounded the `write` capability scope to the
non-privileged `tracker_mirror` verb set (`issue-create`/`issue-update`/`pr-comment`)
and rejected privileged verbs/classes. G2.005.1 made the connector executable as a
**read-only** `ce connector` runtime with a credential-by-reference boundary and an
injectable, offline-disciplined client seam. G2.005.2 makes the bounded write set
executable. It is the first **side-effecting** connector surface — it can mutate a
source host — so it must do so under the tightest activated autonomy envelope without
breaking the repo's offline testing discipline or ever exposing credentials.

## Decision

G2.005.2 extends `validators/creator_engine_validator/connector_runtime.py` with a
write path and adds the `ce connector write-plan`/`submit` subcommands. It reuses the
G2.005.0 validator for all shape decisions and the G2.005.1 credential/client seams,
imports no CE-event/PCL/distributed-identity code, and changes no read-path behavior.

Key boundary decisions:

- **CE `operating_mode: strict` only.** A write executes only when BOTH the connector
  and the Mission-Brief carry `operating_mode: strict`; `auto`/`transcendence` are
  refused before any request (`G2-CONN-MODE-REFUSED`). This makes the `G2.002.1`
  operating-mode dependency enforceable: `auto`/`transcendence` are schema-present but
  unactivated, so the first credential-bearing write surface is confined to the one
  mode with activated semantics. This runtime *autonomy* axis is distinct from the
  *batch strict-mode* governance cadence used to author and ratify the gate.
- **`tracker_mirror`-bounded; non-privileged.** Only `issue-create`/`issue-update`/
  `pr-comment` are permitted; a `read_only` connector/brief routed to the write path
  is refused (`G2-CONN-READONLY-REFUSED`), a verb outside the set is refused
  (`G2-CONN-SCOPE`), and the Mission-Brief must declare the `tracker_mirror` mutation
  class. One bounded mutation per `submit` — no batching, no auto-retry that could
  double-write.
- **Credential REQUIRED by reference.** Unlike reads (which may be anonymous), a write
  REQUIRES a present credential resolved from `credential_ref` at call time, used only
  to construct the request, and never stored in a record, printed, logged, committed,
  or carried in a write-receipt. An absent/`none` credential fails closed before any
  request (`G2-CONN-CREDENTIAL-MISSING`).
- **Network only through an injectable seam.** The default `UrllibGitHubWriteClient`
  (`POST` for `issue-create`/`pr-comment`, `PATCH` for `issue-update`) reaches the
  network only via an injectable `opener`, so tests inject a fake opener and the
  suite/`check` make no real request. Both it and `NullWriteClient` fail closed
  (`G2-CONN-NETWORK`). Request construction and response parsing are unit-tested; only
  the literal socket call is unexercised.
- **Redaction-safe receipts.** Write results are normalized to a bounded field set;
  receipts carry no credential or secret. Optional cache writes target the git-ignored
  `.ce/connector/cache/`.

## Consequences

- The first side-effecting connector is executable and offline-testable, with the
  strict-mode floor, the `tracker_mirror` bound, the required-credential boundary, and
  the redaction-safe receipt enforced at the runtime and reused from the landed
  substrate validator and read runtime.
- Later gates can bind tracker connectors (`G2.005.3`) and — only under their own
  ratification — `auto`/`transcendence` write activation and credential brokering on a
  stable write runtime + client seam.

## Non-ratification statement

This ADR records a design decision for the PR candidate. It ratifies no
`auto`/`transcendence` autonomy, no credential storage/brokering, no
privileged-floor relaxation, no widening of the `tracker_mirror` bound, and no agent
ratification.
