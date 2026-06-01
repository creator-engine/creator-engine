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

Connector write runtime (`G2.005.2`, now landed — see §9), tracker connectors
(`G2.005.3`), credential brokering, CI/deploy, and autonomy activation.

## 9. Write runtime (G2.005.2)

`G2.005.2` adds the strict-mode `ce connector` **write** path over the same
substrate + read runtime. It reuses the `connector`/`mission_brief` validator and
the read runtime's credential/client seams, imports no CE-event/PCL/distributed-
identity code, and changes no read-path behavior. It makes the bounded,
non-privileged `tracker_mirror` write set executable — and only under CE
`operating_mode: strict`.

> **Two distinct "strict" axes.** CE `operating_mode: strict` is the *runtime
> autonomy mode* this gate enforces on records (vs `auto`/`transcendence`). It is
> separate from the *batch strict-mode* governance cadence used to author and
> ratify the gate. This section is about the former.

### Commands

- `ce connector write-plan --connector <f> --mission-brief <f>` — validate a
  `write`-scope connector + `tracker_mirror` Mission-Brief and emit the bounded
  write plan (offline; no secrets).
- `ce connector submit --connector <f> --mission-brief <f> --verb <v> --resource <path> [--payload <json>] [--base-url U]`
  — execute one bounded `tracker_mirror` write (`--verb` ∈
  `issue-create`/`issue-update`/`pr-comment`) via the write client and emit a
  redaction-safe write-receipt. Offline / no-client / absent-credential /
  non-strict / transport failure fails closed.

### Floors

- **CE `operating_mode: strict` only.** A write executes only when BOTH the
  connector and the Mission-Brief carry `operating_mode: strict`; `auto`/
  `transcendence` are refused before any request (`G2-CONN-MODE-REFUSED`).
- **`tracker_mirror`-bounded; non-privileged.** Only `issue-create`/`issue-update`/
  `pr-comment` are permitted; a `read_only` connector/brief routed to the write path
  is refused (`G2-CONN-READONLY-REFUSED`), a verb outside the set is refused
  (`G2-CONN-SCOPE`), and the Mission-Brief must declare the `tracker_mirror`
  mutation class. One bounded mutation per `submit` (no batch, no auto-retry).
- **Credential REQUIRED by reference.** Unlike reads, a write REQUIRES a present
  credential resolved from `credential_ref` at call time; an absent/`none`
  credential fails closed before any request (`G2-CONN-CREDENTIAL-MISSING`). The
  value is never stored, printed, logged, committed, or carried in a write-receipt.
- **Network only through an injectable seam.** The default `urllib` write adapter
  (`POST` for `issue-create`/`pr-comment`, `PATCH` for `issue-update`) reaches the
  network only via an injectable opener; tests inject a fake so the suite is
  network-free, and both it and the null client fail closed offline.
- **Redaction-safe receipts.** Write-receipts carry only bounded result fields,
  never a credential or secret. Optional cache writes go to the git-ignored
  `.ce/connector/cache/`.

### Deferred (after G2.005.2)

Tracker connectors (`G2.005.3`, now landed read-only — see §10), `auto`/
`transcendence` write activation, credential brokering/injection, batching/
multi-write transactions, CI/deploy, merge/queue authority.

## 10. Read-only tracker connectors (G2.005.3)

`G2.005.3` generalizes the read runtime from GitHub-only to **multi-provider** by
adding read-only **Jira** and **GitLab** (REST) adapters over the same read plan +
client seam + receipt machinery. The concrete vendor is selected at invocation by a
runtime `--provider` flag (default `github`); the connector descriptor stays
vendor-neutral (the substrate declares `provider_class` an opaque, non-vendor label
and the connector object is closed), so no descriptor field and no schema change is
introduced. It reuses the `connector`/`mission_brief` validator, changes no GitHub
read/write behavior, and imports no CE-event/PCL/distributed-identity code.

### Commands

- `ce connector fetch --connector <f> --mission-brief <f> --resource <path> --provider {github,jira,gitlab} [--base-url U]`
  — execute one read-only GET via the selected provider adapter and emit a
  redaction-safe read-receipt. `verify`/`plan` are provider-agnostic (offline) and
  unchanged.

### Floors

- **Read-only only.** A `write` scope / non-read verb is refused before any request
  (`G2-CONN-WRITE-REFUSED` / `G2-CONN-SCOPE`) for every provider; tracker adapters
  expose GET only. Tracker **writes** are deferred.
- **Provider by flag.** `--provider` selects the default adapter
  (`github`/`jira`/`gitlab`); an unknown provider fails closed (`G2-CONN-PROVIDER`).
  `github` reproduces the G2.005.1 behavior exactly. Provider-correct auth: GitHub/
  Jira use a `Bearer` header; GitLab uses its native `PRIVATE-TOKEN` header — each
  derived from the credential resolved BY REFERENCE and never logged.
- **Network only through an injectable seam.** Every adapter reaches the network only
  via an injectable opener; tests inject a fake so the suite is network-free, and each
  default adapter fails closed offline.
- **Redaction-safe receipts.** Read-receipts carry only bounded fields, never a
  credential or secret.

### Deferred (after G2.005.3)

Linear (GraphQL) adapter + seam generalization; the tracker **write** runtime
(`tracker_mirror` writes for Jira/GitLab); descriptor-bound provider selection (a
substrate schema change); credential brokering; CI/deploy.
