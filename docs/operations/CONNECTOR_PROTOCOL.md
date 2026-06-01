# Connector Protocol (G2.005.0 substrate)

**Status**: Substrate only. Authored under gate `G2.005.0`. Records and validates
shape only; no connector runtime, no network/API, no credential injection.

**Source-of-truth**: `specs/v2/005-connector-substrate/spec.md` + `spec.ce.yml`.
Schemas: `schemas/connector.schema.yaml`, `schemas/mission-brief.schema.yaml`.
Validator: the `connector` and `mission_brief` checks. Examples:
`validators/examples/connector/`, `validators/examples/mission-brief/`.

## 1. Purpose

`G2.005.0` is the first Phase D gate: the connector coordination **substrate** the
later connector runtime gates (`G2.005.1` GitHub read-only, `G2.005.2` write,
`G2.005.3` tracker) build on. It defines two shape-only record families and the
bounded `tracker_mirror` mutation class.

## 2. Connector descriptor

A connector descriptor declares the shape of a `source_host` or `tracker`
connector: `connector_id` (prefix `conn-`), `connector_kind`, an **opaque
provider-class label** (`provider_class`, e.g. `git-host` / `issue-tracker` — never
a concrete vendor/account binding as normative), a **capability** (`scope`
`read_only`|`write` + bounded `verbs`), a **`credential_ref` BY NAME ONLY**
(`{ref_kind, ref_name}` — never a secret value), `emitting_role`, `operating_mode`,
and an optional `metadata`.

Capability bound (`VAL-CONN-CAPABILITY`): `read_only` verbs come from the read set
(`issue-read`/`pr-read`/`repo-read`/`status-read`); `write` verbs are bounded to
the **`tracker_mirror`** set (`issue-create`/`issue-update`/`pr-comment`). No
privileged verbs.

## 3. Mission-Brief

A Mission-Brief is the bounded task brief a connector carries: `brief_id` (prefix
`mb-`), an opaque `assignment_ref`, `declared_mutation_classes`, a
`capability_scope`, optional `refs` to CE-event/PCL artifacts **by opaque 64-hex
content hash only**, a shape-only `signature`, and optional `metadata`.

`declared_mutation_classes` may contain only the connector-substrate classes
`docs`, `code`, or `tracker_mirror`. A **privileged** class
(`deploy`/`governance`/`identity`/`security`/`attestation`/`redaction`) is a
privilege escalation and fails closed (`VAL-MB-PRIVILEGE-ESCALATION`).

## 4. The `tracker_mirror` mutation class

`tracker_mirror` is a **new, bounded, non-privileged** mutation class for
tracker/issue/PR-comment **mirroring** only. It does **not** grant any privileged
capability, and it does **not** modify the v0.1 baseline mutation-class taxonomy
(`docs/contracts/mutation-class-taxonomy.md`, `schemas/mutation-class.schema.yaml`)
— it is defined and bounded within the connector substrate.

## 5. Invariants (fail-closed)

- **No secrets** — no tokens/credentials/installation-ids/account-names/app-slugs
  as values anywhere; credentials are referenced by name only (`VAL-CONN-SECRET`,
  `VAL-MB-SECRET`, `VAL-CONN-CREDENTIAL-REF`).
- **Privileged floor** — privileged classes remain Operator-only; `agent_ratifier`
  (and legacy `source`) are reserved-inactive and may not emit; connectors and
  Mission-Briefs never ratify.
- **Decoupling** — CE-event/PCL references are opaque 64-hex hashes; the substrate
  imports no runtime code.
- **Operating-mode context** only; **signature** shape-only `reserved-inactive`;
  **no inline metadata** in Markdown; **legacy `.hermes/` write-freeze**.

## 6. State boundary

The canonical future home for connector/Mission-Brief runtime state is under
`.ce/`. `G2.005.0` writes no active state and refuses legacy `.hermes/` targets.

## 7. Out of scope (deferred)

Connector runtime, `ce connector` CLI, network / GitHub / tracker API calls,
credential injection/brokering, live issue/PR mutation, CI/deploy, and
auto/transcendence activation — all deferred to later, separately ratified gates.
