---
slug: ce-fleet-status
date: 2026-06-24
kind: added
scope: validator engine (forge.fleet_status) / ce CLI (fleet status)
issue: ce-fleet-status
---

**Fleet status: one compact aggregate view of CE seats, daemon health, and open
PR board state.**

- Adds `forge.fleet_status` and `ce fleet status`, reusing the sentinel-derived
  `forge.seats_status` read-model for per-seat liveness.
- Adds integrator queue-daemon and review-pickup daemon health from process
  liveness plus explicit JSONL daemon logs, with pure parsers for tests.
- Adds the open-PR board summary through the existing integrator daemon GitHub
  candidate adapter: PR number, review decision, and mergeable state.
- Supports compact human-readable output and `--json`; tests inject all process
  and GitHub seams, with no live processes or network.
