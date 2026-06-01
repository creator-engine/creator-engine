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

## 7. Out of scope of the substrate (G2.005.0)

Connector runtime, `ce connector` CLI, network calls, credential injection/
brokering, live issue/PR mutation, CI/deploy, and auto/transcendence activation —
the read-only runtime is `G2.005.1` (below); write is `G2.005.2`.

## 8. Read-only runtime (G2.005.1)

`G2.005.1` adds the local, daemonless `ce connector` read-only runtime over the
substrate. It reuses the `connector`/`mission_brief` validator and imports no
CE-event/PCL/distributed-identity code.

### Commands

- `ce connector verify --connector <f> --mission-brief <f>` — validate the pair and
  confirm a read plan builds (offline).
- `ce connector plan --connector <f> --mission-brief <f>` — emit the read-only read
  plan (offline; no secrets).
- `ce connector fetch --connector <f> --mission-brief <f> --resource <path> [--base-url U]`
  — execute one read-only GET via the read client and emit a redaction-safe
  read-receipt. Offline / no-credential / transport failure fails closed
  (`G2-CONN-NETWORK`).

### Floors

- **Read-only only.** A `write` scope or non-read verb is refused before any
  request (`G2-CONN-WRITE-REFUSED` / `G2-CONN-SCOPE`); the adapter exposes GET only.
  Write is `G2.005.2`.
- **Credential by reference.** Resolved from `credential_ref` at call time, used
  only to build the request Authorization header, and never stored, printed,
  logged, or committed. `secret_manager_ref` resolution is deferred (fails closed).
- **Network only through an injectable seam.** The default `urllib` adapter reaches
  the network only via an injectable opener; tests inject a fake so the suite is
  network-free, and the default fails closed offline / without a client.
- **Redaction-safe receipts.** Read-receipts carry only bounded fields, never a
  credential or secret. Optional cache writes go to the git-ignored
  `.ce/connector/cache/`.

### Deferred

Connector write runtime (`G2.005.2`), tracker connectors (`G2.005.3`), credential
brokering, CI/deploy, and autonomy activation.
