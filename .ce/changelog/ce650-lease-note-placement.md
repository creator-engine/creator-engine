---
slug: ce650-lease-note-placement
date: 2026-07-25
kind: changed
scope: queue daemon lease maintenance note
issue: ce-ops#650
---

**Make the queue-daemon lease coupling note discoverable.**

- Hoist the single authoritative launcher-coupling note to module scope so it
  precedes every private seam it documents.
