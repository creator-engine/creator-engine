---
slug: ce-docs-stale-wheel-envvar
date: 2026-07-05
kind: changed
scope: docs
issue: ce-docs-stale-wheel-envvar
---

**Document the stale-wheel override in contributor setup.**

- Explain that stale installed validator wheels can refuse gate commands when the source checkout is newer.
- Name `CE_ALLOW_STALE_WHEEL=1` as the explicit one-off override and keep reinstalling or updating the wheel as the durable fix.
