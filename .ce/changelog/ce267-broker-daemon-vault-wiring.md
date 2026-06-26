---
slug: ce267-broker-daemon-vault-wiring
date: 2026-06-26
kind: feat
scope: egress-broker
issue: ce-ops#267
---

**Wire egress-broker daemon to vault signer + AppRole login.**

Adds an `_approle_token_supplier` factory to `ce_egress_self_push_broker.py` that performs a
per-call `POST /v1/auth/approle/login` to OpenBao/Vault using stdlib `urllib` + TLS-verified
via `ssl.create_default_context(cafile=ca_bundle)`. Rewires signer construction in `_build_signer`:
when `seat.secret_ref` is set, reads `BAO_ADDR`/`VAULT_ADDR`, `BAO_CACERT`/`VAULT_CACERT`,
`BROKER_APPROLE_ROLE_ID`, and `BROKER_APPROLE_SECRET_ID` from the environment, builds a
`VaultKvConfig` with the AppRole token supplier, and delegates to `make_signer_for_seat`
(from ce-ops#266). Any missing vault env var on a `secret_ref` seat is a fail-closed
`_BrokerStartupError` — never silently falls back to disk/pem_path. `secret_id`, `role_id`,
and tokens are never logged or included in error messages. Adds `ce-egress-broker.service` to
the systemd install script's `services=()` array with an EnvironmentFile note. New unit tests
cover all five required cases (vault signer build, AppRole login endpoint + token parsing,
fail-closed on missing env, pem_path fallback, no secret leakage in errors/logs).
