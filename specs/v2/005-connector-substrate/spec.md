# Connector substrate (connector descriptor + Mission-Brief)

## Goal

G2.005.0 defines the v2 connector coordination **substrate**: the shape-only
connector descriptor, the Mission-Brief record, and the bounded non-privileged
`tracker_mirror` mutation class — the contracts the later connector runtime gates
(`G2.005.1`–`G2.005.3`) build on. It depends only on the merged `G2.002.0`
operating-mode substrate and completes after Phase C.

## Scope

Substrate only: schemas, validator (`connector` + `mission_brief` checks),
protocol doc, examples, tests, spec/sidecar/ADR, and optional generic templates.
No connector runtime, no `ce connector` CLI, no network/GitHub/tracker API calls,
no credential injection, no live issue/PR mutation. Privileged mutation classes
remain Operator-only; the only bounded write class this substrate permits is
`tracker_mirror`. It imports no runtime/CE-event/PCL/distributed-identity code and
does not modify the v0.1 baseline mutation-class taxonomy.

## Functional requirements

### FR-001 — Connector descriptor

A connector descriptor MUST carry `connector_id` (prefix `conn-`), a
`connector_kind` (`source_host`|`tracker`), an opaque `provider_class` label, a
`capability` (`scope` + `verbs`), a `credential_ref` (by name only),
`emitting_role`, `operating_mode`, and `recorded_at`. Unknown kind fails closed.

### FR-002 — Bounded capability scope

`read_only` verbs MUST come from the read set; `write` verbs MUST be bounded to the
`tracker_mirror` set (`issue-create`/`issue-update`/`pr-comment`). No privileged
verbs.

### FR-003 — Credential by reference; no secrets

`credential_ref` MUST be a `{ref_kind, ref_name}` reference BY NAME ONLY. No
tokens, secrets, installation ids, durable account names, or app slugs may appear
as VALUES anywhere in a connector or Mission-Brief.

### FR-004 — Mission-Brief record

A Mission-Brief MUST carry `brief_id` (prefix `mb-`), an opaque `assignment_ref`,
`declared_mutation_classes`, a `capability_scope`, optional opaque `refs`, a
shape-only `signature`, and `recorded_at`.

### FR-005 — `tracker_mirror` bounded; no privilege escalation

`tracker_mirror` is a new bounded non-privileged class. A Mission-Brief MUST NOT
declare any privileged class (`deploy`/`governance`/`identity`/`security`/
`attestation`/`redaction`); doing so is a privilege escalation and fails closed.
This gate does NOT modify the v0.1 baseline mutation-class taxonomy.

### FR-006 — Opaque pointers; decoupling

CE-event/PCL references MUST be opaque 64-hex content hashes carried in
`refs`. The substrate imports no runtime/CE-event/PCL/distributed-identity code.

### FR-007 — Privileged floor preserved

`emitting_role` MUST be a canonical non-ratifying role; `agent_ratifier` (and
legacy `source`) are reserved-inactive and MUST NOT emit; connectors and
Mission-Briefs never ratify.

### FR-008 — Operating-mode context, signature shape, no inline metadata

`operating_mode` is `strict`/`auto`/`transcendence` (context only). The
Mission-Brief `signature` is shape-only with `value` pinned to `reserved-inactive`.
Record metadata MUST live in sidecars/examples, never inline in Spec Kit Markdown.

### FR-009 — State boundary

The canonical future home is under `.ce/`. G2.005.0 writes no active state and
refuses legacy `.hermes/` active-write targets; it makes no network/API calls.

### FR-010 — Validator coverage

The `connector` and `mission_brief` checks MUST enforce schema shape, kind enum,
role floor, mode enum, credential-by-reference / no-secrets, capability bound,
class / privilege-escalation, opaque-pointer shape, signature shape, no-inline
metadata, and the `.hermes/` write-freeze — each with a targeted `VAL-CONN-*` /
`VAL-MB-*` code.

### FR-011 — Substrate stop line

No connector runtime, `ce connector` CLI, network/GitHub/tracker API, credential
injection/brokering, live issue/PR mutation, CI/deploy, or autonomy activation.

## Success criteria

- Well-formed connector and Mission-Brief examples pass; malformed examples fail
  with targeted `VAL-CONN-*` / `VAL-MB-*` codes.
- No connector/Mission-Brief carries a secret value; `tracker_mirror` is bounded
  and non-privileged; privileged classes are refused.
- The new sidecar passes v2 terminology, role enum, sidecar schema (incl.
  risk-coverage), and crosswalk checks without mutating `specs/v2/_crosswalk.yml`;
  the v0.1 baseline taxonomy is unchanged.
- Prior checks/examples/tests remain unchanged; the full validator suite introduces
  no new failures.
- PR review, approval, merge, and cleanup remain separate Operator-ratified gates.

# G2.005.1 — GitHub connector read-only runtime

## Goal

G2.005.1 turns the merged G2.005.0 connector substrate into a local, daemonless
`ce connector` runtime for **read-only** source-host access. It depends on
G2.005.0 and reuses its validator for every shape decision.

## Scope

Adds `validators/creator_engine_validator/connector_runtime.py`, a `ce connector`
CLI group (`verify`/`plan`/`fetch`), the `.ce/connector/cache/` ignore posture, the
runtime ADR, and this spec/sidecar runtime slice. Read-only only; credentials by
reference; network only through an injectable seam (tests network-free); imports no
CE-event/PCL/distributed-identity code; does not modify the connector/Mission-Brief
schemas or the `connector_substrate` check.

## Functional requirements

### FR-012 — `ce connector verify` / `plan`

`verify`/`plan` MUST validate a connector descriptor + Mission-Brief via the
G2.005.0 validator and build a read-only read plan, fully offline; a write scope is
refused.

### FR-013 — Credential by reference

The credential MUST be resolved from `credential_ref` at call time, used only to
construct the request, and MUST NEVER be stored in a record, printed, logged, or
committed. `none`/absent references resolve as anonymous/absent and a write or
required credential failure fails closed before any request.

### FR-014 — Read-only enforcement

The runtime MUST refuse any `write` capability scope or non-read verb before any
request and route writes to G2.005.2. The default adapter exposes GET only.

### FR-015 — Injectable read-client seam

The network MUST be reached only through an injectable `ReadClient` seam; the
default stdlib-`urllib` GitHub adapter MUST fail closed (`G2-CONN-NETWORK`) on any
transport error or when no client is configured.

### FR-016 — Redaction-safe read-receipt

Read results MUST be normalized into a receipt carrying only bounded fields and no
credential or secret value.

### FR-017 — Offline / network discipline

Tests and `check` MUST be network-free: tests inject a fake client/opener and make
no real request.

### FR-018 — Substrate→runtime stop line

No connector write runtime, credential injection/brokering, tracker connectors,
CI/deploy, or auto/transcendence activation.

## Success criteria (G2.005.1)

- `ce connector verify`/`plan` validate offline; `fetch` round-trips via an injected
  client and returns a redaction-safe receipt; write scope is refused before any
  request; offline/no-client fails closed with `G2-CONN-*` codes.
- No credential/secret value appears in any record, output, log, or commit.
- The full validator suite introduces no new failures; the G2.005.0
  `connector`/`mission_brief` checks, schemas, and `_crosswalk.yml` are unchanged.
- The `ce connector` group is documented (README) and the `ce`-inventory guard +
  offline wheel are reconciled.
- PR review, approval, merge, and cleanup remain separate Operator-ratified gates.
