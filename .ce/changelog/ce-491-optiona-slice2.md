---
slug: ce-491-optiona-slice2
date: 2026-07-08
kind: feature
scope: brain intent materializer
issue: CE-491
---

**Extend the Option A brain append intent materializer dry-run surface.**

- Wire the append-intent XOR gate into local PR preflight beside the direct ledger stale-tail gate.
- Add first-parent `origin/main` intent history scanning, HELD closeout-window evaluation, and a one-cycle materializer run-loop skeleton.
- Harden materializer state/armed-write bounds and add focused unit coverage for scan, closeout, run-loop, and hold-path remediations.
