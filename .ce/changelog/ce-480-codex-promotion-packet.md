---
slug: ce-480-codex-promotion-packet
date: 2026-07-06
kind: added
scope: validator CLI
issue: ce-ops#480
---

**Add Codex controller promotion evidence packet support.**

- Added Codex controller-promotion evidence packet read/write and validation helpers for runtime packets under `.ce/state/controller-evidence/`.
- Wired `ce launch --harness codex` to downgrade controller authority to read-only when the packet is absent or incomplete.
- Added takeover discovery and failure-direction tests for packet absence, incomplete packets, and every required field class.
