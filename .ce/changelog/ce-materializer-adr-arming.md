---
slug: ce-materializer-adr-arming
date: 2026-07-10
kind: added
scope: materializer arming ADR
---

Adds ADR-0015 resolving the materializer pre-arming decisions for authority,
credential custody, and lease topology.

- Arming should happen through a governed PR that flips the constant, plus an
  Operator co-sign artifact under the ratified release-signing model.
- The dedicated App credential is issued via the vault_signer pattern (per-call
  OpenBao KV v2 read → /dev/fd pipe → openssl; key never on disk, never in
  worker env), anchored to the ce-kv/forge/github-apps/<app-name>/private-key
  family from the OpenBao secret-path map.
- The current single-host singleton uses MaterializerLease wrapping
  daemon_lease.acquire("brain-append", ...) in brain_intent_materializer.py,
  with a hard revisit before any second host or instance gains brain-append
  capability.
