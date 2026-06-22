---
slug: ce203-lease-id-length
ticket: ce-ops#203
type: fix
scope: pco-allocator lease_id length bound
---

Bounds the allocator's `lease_id` so long pickup lane ids no longer overflow the
PCO-020 schema and refuse the lease write.

- The live canary post-#200 reached `pco_allocator.allocate_in_place()` but the
  lease write was REFUSED by live PCO-020 validation: pickup's lane id
  (`pickup-<repo>-<n>-<run>`, ~48 chars; `pickup._lane_id`) pushed the naive
  `lease-<lane_id>-<14-digit ts>` derivation to ~69 chars, exceeding the 64-char
  `lease_id` bound `^[a-z0-9][a-z0-9-]{2,63}$`. The cascading
  "unevaluated property 'lease_id'" error followed. `allocate()` never tripped
  because its controller callers pass SHORT lane ids; the #200 tests used short
  synthetic lanes and missed it.
- Adds `pco_allocator._mint_lease_id(lane_id, ts_compact)`:
  `lease-<sha256(f"{lane_id}-{ts_compact}")[:32]>` (38 chars, fixed width). It
  starts with the letter `l` and uses only `[a-z0-9-]`, satisfying BOTH the
  worktree-lease pattern and the stricter container-instance pattern
  (`^[a-z][a-z0-9-]{2,63}$`). The `ts_compact` salt keeps two leases on one lane
  distinct. Applied to BOTH `allocate()` and `allocate_in_place()`.
- Length-independence verified: nothing parses `lease_id` back into lane+ts —
  lease record filenames key on `lane_id`, lease-coverage matches on
  `worktree_path`, and the conflict guard only needs the id to pass the pattern.
- Adds production-length regression tests (real pickup lane format) asserting
  both allocate paths succeed and the on-disk lease/claim/event records pass the
  live schema validators with a bounded, conformant `lease_id`.
