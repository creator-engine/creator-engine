---
slug: ce-373-subprocess-timeouts
date: 2026-07-01
kind: fixed
scope: validator preflight
issue: ce-ops#373
---

**Bound validate-pr network subprocess calls.**

- Added a shared network subprocess timeout override for validate-pr and live onboard GH/git network calls.
- Surfaced simulated subprocess timeouts as actionable preflight/onboard errors instead of hangs.
- **Declared work class:** M
