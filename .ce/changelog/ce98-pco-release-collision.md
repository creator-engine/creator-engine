---
slug: ce98-pco-release-collision
date: 2026-06-15
kind: fixed
scope: substrate / pco-release (Active-Work Ledger events)
issue: creator-engine#98
---

**Fix `pco-release` `claim_released` event filenames colliding within one
second, silently dropping an event.**

`events/YYYY/MM/DD/` is shared across every controller and lane, but the event
id was `claim-released-YYYYMMDDhhmmss` — second resolution only, with no
controller / lane / entropy component. Two `pco-release` calls in the same
second produced the identical filename, so the second `_atomic_write`
overwrote the first and a `claim_released` event was lost. The loss was
invisible: schema validation and `active_work_ledger_conflicts` still PASSED
(each surviving record is individually valid), so nothing flagged the
dropped event.

- New `_event_id(prefix, ts_compact)` helper appends an 8-hex random suffix
  (the module's established `uuid.uuid4().hex[:8]` nonce idiom) →
  `claim-released-YYYYMMDDhhmmss-<8hex>`. Guaranteed unique within the
  per-second, shared-directory scope without a filesystem scan (which would
  race across the per-lane release lock). Stays within the schema's 64-char
  `event_id` bound and pattern.
- Applied at BOTH emission sites — `release()` (`claim_released`) and the
  parallel `allocate()` (`claim_created`) — which share the identical latent
  collision. A new `_event_ts_compact()` seam lets tests pin the second.
- Regression tests: two releases (and two allocates) pinned to the SAME
  second now keep BOTH event files on disk, with distinct event ids; a
  negative check confirms the legacy no-entropy form lost one.

No schema or on-disk record-shape change; the `event_id` field stays
schema-valid. `lease_id` is unchanged (its file path is lane-scoped, so it
never collided).
