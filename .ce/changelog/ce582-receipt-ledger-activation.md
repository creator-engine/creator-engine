---
slug: ce582-receipt-ledger-activation
date: 2026-07-25
kind: added
scope: conveyor receipt-ledger activation
issue: ce-ops#582
---

**Add an explicit, reviewed migration for legacy handled-signal state.**

- Keeps normal discovery fail-closed on unversioned receipt ledgers.
- Adds plan-bound, descriptor-verified migration into sealed terminal receipts,
  preserving the no-re-entry property for already handled signals.
- Adds an atomic, private durable backup and an explicit verified rollback path.
- Documents the Operator-only plan, apply, verification, and rollback flow.
- Restores the legacy name after a pre-publication failure, permits only a
  byte-identical same-plan backup resume, and refuses rollback after v1 history
  diverges from the migrated sealed set.
