---
slug: ce-conveyor-intake-s1
date: 2026-07-08
kind: added
scope: conveyor daemon intake queue dry-run planning
issue: conveyor-intake-s1
---

**Add flag-gated conveyor intake queue planning.**

- Add a file-backed intake queue with `pending/`, `claimed/`, and `done/` states.
- Wire the conveyor daemon runner to log dry-run `WOULD_DISPATCH` plans for idle seats when `CE_CONVEYOR_INTAKE_ENABLED=1`.
- Document the queue layout and keep live dispatch out of this slice.
