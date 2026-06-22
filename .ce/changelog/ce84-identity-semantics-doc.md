---
slug: ce84-identity-semantics-doc
date: 2026-06-22
kind: changed
scope: docs / PCO identity semantics
issue: creator-engine#84
---

Clarified CE ledger identity semantics for concurrent Controller seats.

- Documented how operators should read `controller_id`, `lane_id`,
  `pane_label`, Pane Registry identity, Worktree Lease ownership, and handoff
  pointers together.
- Made explicit that pane ids, terminal ids, role labels, lane-name reuse, and
  handoff pointers are not authority to own a lane.
- Kept the slice documentation-only: no schema changes, runtime launch/refusal
  behavior, validator conflict scans, migrations, or broad design claims.
