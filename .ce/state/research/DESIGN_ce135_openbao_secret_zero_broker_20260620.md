# DESIGN - ce-ops#135 OpenBao Secret-Zero Broker

Date: 2026-06-20
Scope: ce-ops#135 / ce-ops#144 W3
Mutation class: security

## Context

The OpenBao go-live artifacts have landed, and the Operator-side runbook now
creates per-dev AppRoles `ce-dev-1` through `ce-dev-4`. Each AppRole is bound to
one rendered policy over `ce-kv/data/devs/<dev>/runtime/*` and
`ce-kv/metadata/devs/<dev>/runtime/*`.

The remaining gap is secret-zero delivery. A dev seat such as `dev-3` must be
able to obtain a short-lived, least-privilege OpenBao token without storing a
standing SecretID, PEM, or local OpenBao config on disk. `dev-4` is expected to
receive new GitHub App material later; that material should be imported into
OpenBao and delivered through this broker path, not copied into persistent local
files.

## Non-Goals

- No production OpenBao init, unseal, root-token use, or migration.
- No real SecretID, wrapping token, RoleID, PEM, or OpenBao token appears in git,
  records, issue comments, PR bodies, tmux transcripts, or argv examples.
- No direct seat access to the broker's own OpenBao token.
- No host-local steady-state secret files.

## Design

The `SecretIdentityBackend` boundary remains the only provider-specific seam.
OpenBao-specific secret-zero actions are adapter methods on
`OpenBaoSecretIdentityBackend`; a later Vault/HCP-compatible backend can expose
the same value-free request/grant contract.

The broker flow is:

1. Seat asks the broker for secret-zero for its own `seat_id`.
2. Broker validates that `seat_id` is in the allowed dev set and that
   `role_name == "ce-${seat_id}"`.
3. Broker performs the same audit preflight as ordinary secret grants.
4. Broker reads the AppRole RoleID through OpenBao, using its own broker token.
5. Broker creates a wrapped SecretID for that role using `X-Vault-Wrap-TTL`,
   `num_uses=1`, and short SecretID TTL.
6. Broker refuses any unwrapped SecretID response.
7. Broker hands an in-memory payload containing RoleID plus wrapping token to an
   injected delivery function and records only a value-free `SecretZeroGrant`.
8. Seat retrieves the payload from the delivery channel, unwraps once, logs in to
   `auth/approle/login`, and receives an in-memory `OpenBaoAppRoleSession`.
9. Seat constructs `OpenBaoSecretIdentityBackend` from that session and can read
   only paths allowed by the per-dev policy.

The delivery function is intentionally injected. The validator package does not
choose a transport and does not write payloads to disk. Valid delivery refs are
non-file channels such as a broker channel, owner-only Unix socket, stdin-once
pipe, or in-process memory for tests.

## Security Properties

- `SecretZeroGrant.to_record()` contains no RoleID, SecretID, wrapping token, or
  client token.
- `OpenBaoRequest`, `OpenBaoResponse`, `SecretZeroPayload`, and session reprs are
  redacted.
- Broker SecretID issuance fails closed unless the OpenBao audit preflight
  succeeds.
- Dev secret-zero issuance is bound to the concrete dev role, preventing a seat
  from requesting another seat's AppRole.
- Wrapping TTL and SecretID TTL are capped at 10 minutes.
- SecretID `num_uses` is fixed at 1.
- Returned delivery refs are checked so the injected delivery layer cannot
  accidentally use the raw RoleID or wrapping token as the recorded ref.

## Throwaway Test Strategy

Unit tests use injected OpenBao runner/delivery callables. They assert the
adapter emits the expected OpenBao paths and wrapping header, refuses bad
seat/role bindings before I/O, rejects unwrapped SecretID responses, and redeems
the seat token without exposing secret values in records or reprs.

Optional live tests remain local/throwaway only and continue to use
`CE_OPENBAO_BIN`; this design does not require touching production.
