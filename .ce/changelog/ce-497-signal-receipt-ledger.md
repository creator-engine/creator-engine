---
slug: ce-497-signal-receipt-ledger
date: 2026-07-16
kind: added
scope: conveyor discovery
issue: ce-ops#497
---

**Persist fail-closed conveyor handled-signal receipts.**

- Add a versioned, atomically persisted receipt ledger keyed by seat, branch, and SHA.
- Bind receipt state transitions to the discovery/daemon handoff so duplicate and terminal signals cannot re-enter processing.
- Preserve indeterminate push and PR-create outcomes as `uncertain` for reconciliation while known pre-side-effect failures remain terminal.
- Require receipt identities for every armed item and wire the live daemon to the controller-configured discovery receipt state.
