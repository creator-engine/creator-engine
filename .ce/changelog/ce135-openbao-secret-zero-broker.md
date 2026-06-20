# ce-ops#135 - OpenBao secret-zero broker

Date: 2026-06-20

## Changed

- Added the OpenBao secret-zero broker design and value-free contract.
- Extended `OpenBaoSecretIdentityBackend` with per-dev response-wrapped SecretID
  issuance and seat-side AppRole redemption helpers.
- Added unit coverage for short-TTL, single-use wrapping, value-free grant
  records, seat/role binding, redaction, and injected delivery.

## Held

- Production init, unseal, root-token handling, real SecretID minting, real PEM
  import, and live migration remain Operator-held.
