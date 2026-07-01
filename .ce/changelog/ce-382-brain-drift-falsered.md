---
slug: ce-382-brain-drift-falsered
date: 2026-07-01
kind: fix
scope: validators
issue: ce-ops#382
---

**Brain drift validation ignores stale local runtime state.**

- Prefer tracked `.ce/brain/assertions.yaml` for repo-local drift checks even
  when ignored `.ce/state/brain/assertions.yaml` exists.
- Keep canonical artifact drift fail-closed while adding regression coverage for
  stale local state and genuine canonical divergence.
