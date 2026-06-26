# Controller Runtime Contract Protocol

**Requirement**: RV1-020 (PCO v1 Gate 2 — Controller Runtime Contract + State Boundary).
**Type**: SVC (schema + validator + CLI). Strict TDD.
**Status**: Substrate/validator authored for host-local legacy and contained
Controller posture. Runtime supervisor (G3), worker runtime (G5),
packaging/launcher (G6), and fan-in (G7) remain later gates.

---

## 1. Purpose

A **Controller Runtime Contract** is a declarative record that classifies the
Controller role, Controller seat, containment posture, and harness authority
boundary for the Creator Engine v1.0 **governed runtime kernel**. It answers
three questions without granting any authority itself:

- *What role is being classified?* — always `role: controller`.
- *Where does Controller authority live?* — legacy `host-local` or contained
  runtime posture, never hosted.
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
| `role` | Always `controller`. |
| `controller_seat` | `{ authority_locality: host-local\|contained, seat: controller }`. Contained records also carry `containment`. |
| `harness` | `{ name: <hermes\|claude-code\|codex> }` — the harness class the contract is recorded under. |
| `authority_boundary` | Seat↔harness classification (see §3). |
| `state_boundary` | Host-local records use `.hermes/`; contained records use `.ce/state/`. Durable account and provider authority are always `none`. |
| `record_timestamp` | ISO-8601 / `commit:` / `source-controlled:` timestamp. |

Unknown top-level fields are refused (strict `unevaluatedProperties: false`).

Contained Controller records extend `controller_seat`:

```yaml
controller_seat:
  authority_locality: contained
  seat: controller
  containment:
    isolation_backend: gvisor-proxy
    forbidden_surfaces:
      - host-home
      - host-tmux-socket
      - host-ssh-agent
      - host-git-push
      - acp-host-transport
      - raw-host-tui
      - docker-socket
      - podman-socket
      - containerd-socket
      - openbao-root-token
      - ce-root-v1-private-key
      - github-app-private-key
    credential_handles:
      max_auth: max-auth-via-setup-token
      ce_root_v1: ce-root-v1-via-openbao
      ce_root_v1_signing: ce-root-v1-signing-request
      github_app: github-app-installation-token
```

The forbidden-surface floor makes the GPU host Controller posture explicit:
contained Controller records must not depend on host home, host tmux socket,
host SSH agent, host `git push`, ACP host transport, raw host TUI authority,
container runtime sockets, OpenBao root token, `ce-root-v1` private key, or
GitHub App private key. Max authentication is represented only by the
`max-auth-via-setup-token` request handle, and `ce-root-v1` signing is
represented only by the `ce-root-v1-via-openbao` request handle. The
`ce-root-v1-signing-request` and `github-app-installation-token` strings are
non-private-key request/handle names, not embedded secret values.

## 3. Authority boundary classification

`authority_boundary` carries three arrays whose membership the validator
enforces beyond the schema:

- `in_seat_harnesses` **must be exactly** `{hermes, claude-code, codex}`. These
  are the harnesses that may operate inside the Controller seat for v1.0.
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

## 4. Controller identity exclusivity

`controller_id` is the durable live-exclusive mutation authority identity for a
Controller within a repo/project/profile scope. It is distinct from concrete
runtime identity: process id, tmux session/window/pane, sentinel `seat_id`, and
harness session ids are observational evidence for where the identity is
running. They do not mint ownership authority and they do not make two
mutation-capable seats for the same `controller_id` valid.

Future `ce launch` / `ce hud` behavior MUST refuse a duplicate live
mutation-capable Controller seat for the same `controller_id` before side
effects. The only contract-level exceptions are:

- attaching to or resuming the already-live seat for that identity;
- a ratified transfer or terminalization that closes the old live authority
  before opening the new one;
- explicit read-only observer mode, with mutation disabled and no claim that
  the observer holds Controller mutation authority.

Pane Registry and seat-sentinel evidence MAY inform the duplicate-live-seat
decision, but they are not ownership authority. The Active-Work Ledger
`controller_id` semantics documented for creator-engine/creator-engine#84 cover
ledger identity; this section records the runtime launch/refusal contract for
creator-engine/creator-engine#89.

## 5. Redaction safety

No field may contain a token value, API key, OAuth refresh token, source-host
installation ID, model API key, account name, browser session cookie, or any
other secret/provider-authority value. The validator refuses secret-bearing key
names and secret-shaped values anywhere in the record with **`RV1-020-SECRET`**.
`state_boundary.durable_account_authority` and `state_boundary.provider_authority`
must both be `none`.

## 6. Validation

```bash
PYTHONPATH=validators python3.14 -m creator_engine_validator.cli \
  scan-controller-runtime-contract examples/well-formed/controller-runtime-contract
```

Validation codes:

| Code | Meaning |
|---|---|
| `RV1-020` | Schema violation (missing/unknown field, bad const/enum, bad timestamp). |
| `RV1-020-AUTH` | Authority-boundary misclassification. |
| `RV1-020-CONTAINMENT` | Contained Controller posture is incomplete or mismatched. |
| `RV1-020-SECRET` | Secret or provider-authority value present in a field. |

## 7. Scope boundary

This protocol is substrate/validator work only. It does **not** implement `ce`,
`ce launch`, `ce hud`, packaging, install, worker runtime, the Side-Effect
Ledger runtime, or fan-in. The companion state boundary is defined in
[`STATE_BOUNDARY_PROTOCOL.md`](STATE_BOUNDARY_PROTOCOL.md).

The duplicate Controller-seat exclusivity text added for
creator-engine/creator-engine#89 is docs/design only. It introduces no runtime
behavior, schema field, validator check, test, GitHub authority, credential
authority, or provider/account change.
