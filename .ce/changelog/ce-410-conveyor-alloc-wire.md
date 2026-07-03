---
slug: ce-410-conveyor-alloc-wire
date: 2026-07-03
kind: fixed
scope: conveyor daemon allocation provenance
issue: ce-ops#410
---

Wires armed conveyor execution to daemon-issued path allocation receipts.

- Removed the default-true item path provenance bit and made raw discovery
  mappings data-only, with no executable paths or receipt.
- Armed conveyor runs now require an injected `DaemonPathAllocator`, allocate
  paths for data-only items before prepare/land/push/PR, and reject direct item
  paths without a receipt valid for the current allocator instance.
- Added secret-free allocation audit logging with allocation id, item key,
  root-relative paths, mode-check results, and cleanup status.
