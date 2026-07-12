---
slug: ce-539-checkpoint-verb-protocol
date: 2026-07-12
kind: added
scope: controller ergonomics
issue: ce-ops#539
---

**Add a deterministic local-only checkpoint verb and agent protocol.**

- Validate labeled, redaction-safe handoff facts before atomically persisting an owner-only resume record.
- Report the exact persisted-byte hash without asserting authority, gate status, or `/clear` completion.
