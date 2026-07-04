---
slug: ce-388-conveyor-discovery
date: 2026-07-04
kind: added
scope: conveyor daemon discovery
issue: ce-388
---

**Add seat-signal discovery for conveyor harvest pickup.**

- Adds a `ConveyorSeatDiscoveryRunner` that probes daemon-owned seat commands,
  parses `READY-FOR-HARVEST` pane signals, validates canonical branch slugs,
  and emits only the four data fields accepted by the conveyor payload schema.
- Adds daemon-owned JSON dedupe state for processed `(seat_id, branch, sha)`
  triples, with corrupt-state recovery and atomic tmp-plus-rename writes.
- Covers ANSI, bullet, wrapped-line, placeholder, diff-echo, last-signal-wins,
  hostile pane text, schema compatibility, and slug-mismatch behavior with
  focused unit tests.
