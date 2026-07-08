---
slug: ce-888-hygiene-n1n3
date: 2026-07-07
kind: fix
scope: brain hydration
issue: CE-888
---

**Post-merge hygiene for resume-state hydration.**

- Select the newest resume-state file by lexicographic path order, matching the timestamped filename convention, with digest only as a tiebreaker.
- Keep seeded resume-state hydration byte-identical across mtime-only touches.
- Reuse the already-computed resume-state digest when returning the hydration pointer.
