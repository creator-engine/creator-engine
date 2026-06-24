---
slug: ce-auto-carrier
date: 2026-06-24
kind: added
scope: validator tooling
issue: ce-ops#21
---

**auto-carrier — ce carrier generates + self-verifies changelog + path-manifest.**

- Added a reusable carrier generator for changelog fragments and self-inclusive PR path manifests.
- Added the ce carrier CLI flow to write, stage, and fail-closed verify carriers against the staged PR diff.
- Covered canonical path-set hashing, parser round-trips, changelog frontmatter, deterministic ordering, and write ordering with offline tests.
