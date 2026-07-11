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
- Add a verified seat-pull handoff adapter with concrete normal work-claim/territory evidence, no-follow brief snapshots, and canonical launch metadata.
- Fence finite-TTL queue ownership with opaque claim tokens and generations, serialize stale-reclaim/launch transitions, and hand launchers a descriptor-anchored snapshot that fails closed on replacement.
- Recover or refuse queue crash windows deterministically, durably publish snapshots without partial final bytes, and close retained descriptors on fence-transition refusal.
- Bind publication and lifecycle lookup to stable unit identity across priority and JSON/YAML filename variants; refuse malformed queue input and invalid bounded claim TTLs as structured seat-pull outcomes.
- Treat malformed or schema-invalid pending records as structured queue-state refusals rather than empty work, normalize controller-evidence parser failures through owned-claim release, and preserve fractional TTL precision through launch fencing.
