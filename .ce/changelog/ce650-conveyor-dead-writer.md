---
slug: ce650-conveyor-dead-writer
date: 2026-07-25
kind: fixed
scope: conveyor daemon ledger persistence
issue: ce-ops#650
---

Remove the unused, unhardened ledger-path writer fallback from the conveyor
daemon. The only remaining ledger writer is the caller-injected hardened seam,
and a regression test rejects attempts to recreate the removed fallback.
