---
slug: ce-460-digest-case-placeholder-residue
date: 2026-07-06
kind: fix
scope: validators
issue: ce-ops#460
---

**Normalize surface digest case and reject manifest-list child digest residue.**

- Normalize SHA256 digest parsing and Dockerfile comparison to lowercase so uppercase hex fixtures match canonical pins.
- Reject per-architecture child-manifest digest maps on surfaces whose policy requires an index/manifest-list digest.
- Cover uppercase digest handling and manifest-list child digest residue in surfaces manifest unit tests.
