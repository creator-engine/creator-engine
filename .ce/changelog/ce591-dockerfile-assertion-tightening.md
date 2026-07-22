---
slug: ce591-dockerfile-assertion-tightening
date: 2026-07-22
kind: fixed
scope: validator static image-contract tests; no runtime surface
issue: #591
---

**Tighten VPS static image-contract assertions.**

- Tighten VPS static image-contract assertions so package installs, offline inputs, and inherited tools must occur in uncommented RUN commands with exact token boundaries.
- Pin the VPS runtime probe to Python 3.14 and prove comment-only, adjacent-token, Python 3.13, and Python 3.15 fixtures cannot satisfy the contracts.
- Leave DGX exact-version tightening out of this carrier: its dormant Dockerfile BRE matcher is defective and is tracked separately as #647; no Dockerfile or other production path changes here.
