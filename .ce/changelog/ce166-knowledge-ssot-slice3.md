---
slug: ce166-knowledge-ssot-slice3
date: 2026-06-26
kind: added
scope: knowledge-ssot self-identity
issue: ce-ops#166
---

**Knowledge-SSOT self-identity drift detection.**

- **Declared work class:** story
- Added live self-identity and worker-spawn runtime probes to derive host/runtime facts from current process, OS, tailnet, GPU, architecture, and worktree surfaces.
- Added bootstrap-time reconciliation for per-seat self-identity probe assertions so remembered identity claims fail closed with loud log output on live drift.
- Seeded authoritative brain assertions and focused unit coverage for deterministic probes and mutated runtime identity.
