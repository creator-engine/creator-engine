---
slug: ce-611-runtime-policy-recovery-proof
date: 2026-07-18
kind: fix
scope: runtime-policy recovery tests
issue: ce-ops#611
work_class: XS
---

**Prove runtime-policy recovery against distinguishable replacement bytes.**

- Strengthens the recovery-rename failure matrix so both destinations contain
  deterministic proposed bytes before best-effort restoration begins.
- Proves ordered restore attempts, original-byte recovery, retained backups for
  failed restores, initiating-error chaining, and temporary-file cleanup.
- This is a test-only `XS` slice; the forge label remains compatible as `wc:S`.
