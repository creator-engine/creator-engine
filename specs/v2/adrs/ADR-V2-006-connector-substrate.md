# ADR-V2-006: Connector substrate (connector descriptor + Mission-Brief + tracker_mirror)

## Status

Accepted for G2.005.0 draft substrate.

## Context

Creator Engine v2's Phase D needs a connector coordination substrate before any
connector runtime (GitHub / tracker read or write) exists. With Phase C complete,
`G2.005.0`'s dependency floor (`G2.002.0` operating-mode substrate) is met. The
substrate must name connector shape and a connector's bounded task brief without
binding concrete vendors/accounts as normative, without carrying any secret
material, and without escalating beyond a bounded, non-privileged write surface.

## Decision

`G2.005.0` defines two shape-only record families and one new mutation class:

- **Connector descriptor** (`schemas/connector.schema.yaml`): `connector_kind`
  (`source_host`/`tracker`), an opaque `provider_class` label, a `capability`
  (`read_only` reads or a bounded `write` set), and a `credential_ref` **by name
  only**. Concrete vendor/account/app-slug/installation bindings are deployment-time
  overlay decisions, never normative here (per the reviewer-identity §c precedent).
- **Mission-Brief** (`schemas/mission-brief.schema.yaml`): a bounded task brief —
  opaque `assignment_ref`, `declared_mutation_classes`, `capability_scope`, opaque
  64-hex `refs` to CE-event/PCL artifacts, and a shape-only `signature`.
- **`tracker_mirror`**: a NEW **bounded, non-privileged** mutation class for
  tracker/issue/PR-comment mirroring (`issue-create`/`issue-update`/`pr-comment`).

Key boundary decisions:

- **No secrets.** Credentials are referenced by name; the validator fails closed on
  any token/secret/installation-id/account/app-slug value (`VAL-CONN-SECRET`,
  `VAL-MB-SECRET`).
- **No privilege escalation.** A Mission-Brief may declare only `docs`/`code`/
  `tracker_mirror`; any privileged class fails closed. `tracker_mirror` does **not**
  modify the v0.1 baseline mutation-class taxonomy — it is defined and bounded
  within the connector substrate.
- **Decoupling.** CE-event/PCL references are opaque 64-hex hashes; the validator
  imports no runtime code.
- **Operator-only floor.** `agent_ratifier` reserved-inactive; connectors and
  Mission-Briefs never ratify; `signature` stays shape-only `reserved-inactive`.

`G2.005.0` implements no connector runtime, `ce connector` CLI, network/GitHub/
tracker API call, credential injection, or live issue/PR mutation. Those are the
deferred runtime gates `G2.005.1`–`G2.005.3`.

## Consequences

- The connector and Mission-Brief shapes are stable for later runtime gates to
  bind real credentials/transports against, with the bounded `tracker_mirror`
  write surface fixed and non-privileged.
- The no-secrets and no-privilege-escalation floors are enforced at the substrate,
  so a connector/Mission-Brief artifact is safe to track and review.

## Non-ratification statement

This ADR records a design decision for the PR candidate. It ratifies no future
runtime authority, no privileged-floor relaxation, no concrete vendor/account
binding, and no agent ratification.
