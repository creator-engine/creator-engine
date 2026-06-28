---
slug: ce-345-path-manifest-dstatus
date: 2026-06-28
kind: fixed
scope: validator tooling
issue: ce-ops#345
---

**path manifest D-status carrier cleanup.**

- Exclude D-status orphan carrier deletions from the per-PR active carrier count.
- Delete the stale ce291a orphan carrier and changelog fragments.
