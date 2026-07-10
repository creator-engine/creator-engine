---
slug: ce-n11s1-intake-queue-substrate
date: 2026-07-10
kind: added
scope: conveyor intake queue
issue: N-11 slice 1
---

**Add durable conveyor intake claim lifecycle.**

- Pin queued briefs by SHA, declare controller path territory, and retain legacy queue APIs.
- Add atomic claim/release/complete transitions, TTL stale reclaim, and a best-effort append-only NDJSON claim ledger.
- Add a verified, injected seat-pull handoff adapter and numeric six-digit-safe priority ordering.
