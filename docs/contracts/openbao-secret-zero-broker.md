# OpenBao Secret-Zero Broker Contract

This contract defines the value-free interface for minting and redeeming
per-dev OpenBao secret-zero. It extends the ADR-0005
`SecretIdentityBackend` seam and is provider-swappable.

## Broker Issue Contract

Input:

- `run_id`: governed run or seat-start identifier.
- `requester_seat_id`: authenticated requester seat; must equal `seat_id`.
- `seat_id`: concrete dev seat, currently `dev-1` through `dev-4`.
- `role_name`: must equal `ce-${seat_id}`.
- `auth_mount`: OpenBao AppRole auth mount, default `approle`.
- `wrap_ttl_seconds`: positive, max 600.
- `secret_id_ttl_seconds`: positive, max 600.
- `secret_id_num_uses`: exactly 1.
- `delivery`: one of `broker-channel`, `unix-socket`, `stdin-once`, or `memory`.
- `delivery_ref`: value-free delivery channel reference whose scheme is one of
  `broker-channel`, `unix-socket`, `stdin-once`, or `memory`, and whose scheme
  is bound to `request.delivery` by code before OpenBao I/O. The schema can
  validate only that the scheme is on the allowlist because grant records do
  not include `request.delivery`. The scheme check is performed after trimming
  and is case-insensitive. Bare or local paths (`/tmp/...`, `./...`, `~/...`),
  UNC paths, `data:` refs, unknown schemes, and raw credential values are
  refused before OpenBao I/O.

Broker behavior:

1. Validate the requester/seat/role binding before OpenBao I/O.
2. Run OpenBao health/audit preflight and fail closed if audit is unavailable.
3. Read the dev AppRole RoleID.
4. Create a response-wrapped SecretID using the wrapping TTL header.
5. Refuse any response that exposes an unwrapped `secret_id`.
6. Invoke the injected delivery function with an in-memory payload.
7. Return `SecretZeroGrant` metadata only.

## Seat Redeem Contract

Input:

- `seat_id`
- `role_name == ce-${seat_id}`
- in-memory RoleID supplier
- in-memory wrapping-token supplier
- injected OpenBao runner

Seat behavior:

1. Unwrap the wrapping token exactly once through `/v1/sys/wrapping/unwrap`.
2. Log in through `/v1/auth/<mount>/login`.
3. Return an in-memory `OpenBaoAppRoleSession`.
4. Build `OpenBaoSecretIdentityBackend` from the session for later
   least-privilege runtime secret reads.

## Prohibited Surfaces

The following must not be written to persistent local disk, git, governance
records, issue comments, PR bodies, argv examples, or tmux transcripts:

- OpenBao root token
- unseal shares
- RoleID values
- SecretID values
- wrapping token values
- OpenBao client tokens
- GitHub App PEM contents

Only value-free refs and accessors may be recorded.
