---
slug: ce-410-conveyor-alloc-wire
date: 2026-07-03
kind: fixed
scope: conveyor daemon allocation provenance
issue: ce-ops#410
---

**slice 2: conveyor daemon allocation receipts (armed-path provenance).**

- Replaced the default-true `daemon_owned_paths_allocated` bit with `DaemonPathAllocator` receipts; raw discovery mappings via `from_mapping` stay data-only.
- Armed conveyor construction now refuses without an injected allocator; armed runs allocate receipted paths for data-only items before prepare/land/push/PR and reject direct item paths lacking a valid receipt for the current allocator instance.
- Retained confinement checks as defense-in-depth alongside allocator receipts.
- Added secret-free allocation audit logging (allocation id, item key, root-relative paths, mode-check results, cleanup status).
