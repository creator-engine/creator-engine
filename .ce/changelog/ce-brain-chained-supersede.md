---
slug: ce-brain-chained-supersede
date: 2026-07-02
kind: fixed
scope: brain runtime
issue: ce-brain-chained-supersede
---

**Chained brain assertion supersedes.**

- Fixed the single-level supersede cap in brain assertion current-view validation.
- Relaxed only superseded_by target resolution: supersede chains may pass through superseded records, but must terminate at exactly one active assertion; cycles are rejected.
- This unblocks evidence re-pins on assertions already at -v2 without changing append mechanics, record shape, or ledger content.
