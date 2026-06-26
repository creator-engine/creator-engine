---
slug: ce266-broker-openbao-minter
date: 2026-06-26
kind: feat
scope: egress-broker
issue: ce-ops#266
---

**wire egress-broker minter to OpenBao App-key custody.**

Add vault-backed signer (`vault_signer`) that fetches the App private key from OpenBao KV v2 per-call via an injectable `VaultFetcher`, pipes it to `openssl` through `/dev/fd/<N>` (anonymous pipe — key never touches disk), then zeroes in-memory bytes. The `SeatAppConfig` now accepts either `pem_path` (legacy, dev-2/dev-4) or `secret_ref {mount, path, field}` (preferred per ce-ops#266, dev-3). `make_signer_for_seat()` routes to the correct signer. `VaultKvConfig` carries injectable address/CA/token seams (address from `BAO_ADDR`/`VAULT_ADDR`; runtime token provided at deploy time; never embedded). Fail-closed: vault read error → `EgressSignerError`, never fallback. No key material in logs/repr. 29 new unit tests; 32 existing pass; 0 new failures vs baseline.
