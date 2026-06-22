---
slug: ce200-belt-lane-claim-allocation
ticket: ce-ops#200
type: fix
scope: pickup belt lane claim allocation
---

Unblocks the belt's autonomous `--enable-launch` path.

- `ce pickup poll --claim --enable-launch` claimed a forge ticket then invoked
  `ce lane launch`, which hard-requires a live, unreleased Active-Work claim
  YAML (RV1-030, `G3-CLAIM-MISSING`). Nothing on the belt path allocated that
  claim, so every belt-launched lane refused with exit 1.
- Adds `pco_allocator.allocate_in_place`: the claim-allocation half of
  `pco-allocate` without `git worktree add` or the root-checkout refusal, for an
  EXISTING in-place checkout. It writes a lease + claim + event under the lane
  lock, keeping the claim lease-covered (`PCO-021`) and conflict-guard clean.
- `pickup.launch_lane` now allocates the in-place lease+claim+event in the SAME
  ledger root the launch argv forwards to `--ledger-root`, BEFORE the spawn, so
  poll→claim→allocate→launch→`LAUNCHED_STATE` works end to end.
- Idempotent + fail-closed: a re-poll of an already-claimed item reuses the live
  claim (no double-allocation, no crash); allocator refusals fail the launch
  closed with a redaction-safe note.
- Adds offline end-to-end coverage asserting the claim+lease exist before the
  spawn and an idempotency re-poll test.
