---
slug: ce-materializer-adr-arming
date: 2026-07-10
kind: added
scope: materializer arming ADR
---

Adds a short ADR resolving the materializer pre-arming decisions for authority,
credential custody, and lease topology.

- Arming should happen through a governed PR that flips the constant, plus an
  Operator co-sign artifact under the ratified release-signing model.
- The dedicated App credential should be issued through OpenBao with a short
  TTL and no worker-disk private key exposure.
- The current single-host singleton may use the local file lease, with a hard
  revisit before any multi-instance materializer topology.
