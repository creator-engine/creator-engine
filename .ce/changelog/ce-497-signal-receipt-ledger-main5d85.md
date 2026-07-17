---
slug: ce-497-signal-receipt-ledger-main5d85
date: 2026-07-16
kind: added
scope: conveyor discovery
issue: ce-ops#497
---
**Persist fail-closed conveyor handled-signal receipts.**
- Add a versioned, atomically persisted receipt ledger keyed by seat, branch, and SHA.
- Bind receipt state transitions to the discovery/daemon handoff so duplicate and terminal signals cannot re-enter processing.
- Preserve indeterminate push and PR-create outcomes as `uncertain` for reconciliation while known pre-side-effect failures remain terminal.
- Require receipt identities for every armed item, wire the live daemon to the controller-configured discovery receipt state, reject typed identity branch mismatches, and require the configured controller receipt ledger before any armed allocation or side effect. Persist a permanent `completion_sealed` marker in one terminal replacement, block and audit sealed restart entries by fingerprint, retain legacy `completion_pending` fail-closed behavior, and fail closed on post-replace durability uncertainty. Harden the private receipt directory, lock, ledger, and temporary publication flow with lexical path validation, descriptor-relative no-follow traversal, exact owner/mode/link checks, component identity revalidation, and crash-durable fsync ordering; terminal completion ambiguity remains value-free `uncertain` after a side effect and stable `failed` before one.
