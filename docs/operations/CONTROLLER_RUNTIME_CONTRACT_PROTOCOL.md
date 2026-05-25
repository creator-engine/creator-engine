# Controller Runtime Contract Protocol

**Requirement**: RV1-020 (PCO v1 Gate 2 — Controller Runtime Contract + State Boundary).
**Type**: SVC (schema + validator + CLI). Strict TDD.
**Status**: Substrate/validator authored. Runtime lane-launch (G3), worker
runtime (G5), packaging/launcher (G6), and fan-in (G7) remain later gates.

---

## 1. Purpose

A **Controller Runtime Contract** is a declarative record that classifies the
Controller seat and the harness authority boundary for the Creator Engine v1.0
**local governed runtime kernel**. It answers two questions without granting
any authority itself:

- *Where does Controller authority live?* — host-local, not hosted.
- *Which harnesses operate inside the Controller seat, which are seam, and which
  are never authorized for v1.0 kernel authority?*

The record is **declarative and validated only**. Validating or authoring a
Controller Runtime Contract does **not** launch a pane, call Claude, call
GitHub, call any network API, or mutate runtime state. It is an evidence/contract
artifact, not a runtime command.

## 2. Record shape

Schema: [`../../schemas/controller-runtime-contract.schema.yaml`](../../schemas/controller-runtime-contract.schema.yaml).
Canonical example:
[`../../examples/well-formed/controller-runtime-contract/minimal.yaml`](../../examples/well-formed/controller-runtime-contract/minimal.yaml).

Required fields:

| Field | Meaning |
|---|---|
| `kind` | Always `controller-runtime-contract`. |
| `schema_version` | Starts at `"1"`. |
| `controller_seat` | `{ authority_locality: host-local, seat: controller }` — explicitly host-local Controller authority. |
| `harness` | `{ name: <hermes\|claude-code\|codex> }` — the harness class the contract is recorded under. |
| `authority_boundary` | Seat↔harness classification (see §3). |
| `state_boundary` | `{ state_root: .hermes/, durable_account_authority: none, provider_authority: none }`. |
| `record_timestamp` | ISO-8601 / `commit:` / `source-controlled:` timestamp. |

Unknown top-level fields are refused (strict `unevaluatedProperties: false`).

## 3. Authority boundary classification

`authority_boundary` carries three arrays whose membership the validator
enforces beyond the schema:

- `in_seat_harnesses` **must be exactly** `{hermes, claude-code, codex}`. These
  are the harnesses that may operate inside the host-local Controller seat for
  v1.0.
- `seam_harnesses` **must include** `openclaw`. OpenClaw is a seam, never an
  in-seat harness.
- `unauthorized_authorities` **must include** `hosted-service`, `saas`, and
  `github-connector`. Hosted service / SaaS / GitHub connector are **not
  authorized** for v1.0 kernel authority.

A hosted/SaaS/GitHub-connector authority appearing in `in_seat_harnesses`, or
OpenClaw appearing as in-seat, or a missing in-seat harness, is refused with
**`RV1-020-AUTH`**.

> Even though the contract classifies Codex as an in-seat harness class, the
> visible Gate 2 implementation lane itself is **Claude Code Opus 4.7, effort
> high**, only.

## 4. Redaction safety

No field may contain a token value, API key, OAuth refresh token, source-host
installation ID, model API key, account name, browser session cookie, or any
other secret/provider-authority value. The validator refuses secret-bearing key
names and secret-shaped values anywhere in the record with **`RV1-020-SECRET`**.
`state_boundary.durable_account_authority` and `state_boundary.provider_authority`
must both be `none`.

## 5. Validation

```bash
PYTHONPATH=validators python3.14 -m creator_engine_validator.cli \
  scan-controller-runtime-contract examples/well-formed/controller-runtime-contract
```

Validation codes:

| Code | Meaning |
|---|---|
| `RV1-020` | Schema violation (missing/unknown field, bad const/enum, bad timestamp). |
| `RV1-020-AUTH` | Authority-boundary misclassification. |
| `RV1-020-SECRET` | Secret or provider-authority value present in a field. |

## 6. Scope boundary

This protocol is substrate/validator work only. It does **not** implement `ce`,
`ce launch`, `ce hud`, packaging, install, worker runtime, the Side-Effect
Ledger runtime, or fan-in. The companion state boundary is defined in
[`STATE_BOUNDARY_PROTOCOL.md`](STATE_BOUNDARY_PROTOCOL.md).
