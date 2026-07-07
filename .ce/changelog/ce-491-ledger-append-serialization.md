---
slug: ce-491-ledger-append-serialization
date: 2026-07-07
kind: changed
scope: validators
issue: ce-ops#491
---

**Brain ledger append serialization slice 1.**

- Added a local PR preflight guard that refuses `.ce/brain/assertions.yaml`
  deltas when the live base ledger tail has moved since the PR merge base.
- Documented the mediated append target and slice 1 deferrals.
