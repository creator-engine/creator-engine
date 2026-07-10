---
slug: ce-469-verify-install-root
date: 2026-07-10
kind: fixed
scope: validators
---

**Verify installs against the requested install root.**

`ce verify-install` now reports the effective root in machine-readable output
and refuses install-state or live venv probes that resolve outside that root.
