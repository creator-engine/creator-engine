---
slug: ce-423-tenant-denylist-matrix
date: 2026-07-06
kind: changed
scope: validator confidentiality
issue: creator-engine/ce-ops#423
---

**Tenant denylist matrix.**

- Added a tenant confidentiality denylist matrix loader for data-driven tenant patterns, venue routing, and per-tenant shrink-only allowlists.
- Threaded the matrix through the public confidentiality scan so CE forbidden patterns stay unconditional while tenant identifiers are blocked on CE public and cross-tenant surfaces.
- Added focused coverage for denylist refs, bidirectional enforcement, CE-floor enforcement in tenant venues, tenant allowlist ratchets, and PR/issue/evidence scan surfaces.
