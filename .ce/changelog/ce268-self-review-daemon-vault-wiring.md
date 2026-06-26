---
slug: ce268-self-review-daemon-vault-wiring
date: 2026-06-26
kind: feat
scope: egress-broker
issue: ce-ops#268
---

**Wire the self-review broker daemon to vault signer + AppRole login (mirrors ce-ops#267).**

Adds an `_approle_token_supplier` factory + `_build_signer` + `_BrokerStartupError` to
`ce_egress_self_review_broker.py`, copied verbatim from the merged self-PUSH broker (ce-ops#267)
so both credential paths share identical security properties. The supplier performs a per-call
`POST /v1/auth/approle/login` to OpenBao/Vault using stdlib `urllib`, TLS-verified via
`ssl.create_default_context(cafile=ca_bundle)`. Signer construction now routes by key source:
when `seat.secret_ref` is set the daemon reads `BAO_ADDR`/`VAULT_ADDR`, `BAO_CACERT`/`VAULT_CACERT`,
`BROKER_APPROLE_ROLE_ID`, and `BROKER_APPROLE_SECRET_ID` from the environment, builds a
`VaultKvConfig` with the AppRole token supplier, and delegates to `make_signer_for_seat`
(from ce-ops#266); `pem_path` seats keep the openssl signer. Any missing vault env var on a
`secret_ref` seat is a fail-closed `_BrokerStartupError`, surfaced as a refusal — never a silent
fall-back to disk/pem_path. `secret_id`, `role_id`, and tokens are never logged or included in
error messages; only `seat_id` + `vault-backed`/`pem-backed` is logged. The existing
`signer=`-injection seam is preserved for back-compat (tests/explicit injection win).

Adds a new `ce-egress-self-review.service` systemd unit (mirroring `ce-egress-broker.service`)
and registers it in the install script's `services=()` array with an EnvironmentFile note for the
required vault env vars. New unit tests cover all five required cases (vault signer build, AppRole
login endpoint + token parsing, fail-closed on missing env, pem_path openssl path, no secret
leakage in errors/logs); the 8 existing self-review broker tests (ce-ops#243) still pass.
