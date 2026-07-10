---
slug: ce-f1s2-preflight-env-propagation
date: 2026-07-10
kind: fix
scope: preflight subprocess environment propagation
---

Preserve caller-provided pytest temporary-directory and option settings when preflight launches inner test suites.
