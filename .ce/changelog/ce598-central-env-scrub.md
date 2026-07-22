---
slug: ce598-central-env-scrub
date: 2026-07-22
kind: changed
scope: validator GitHub child environments
issue: ce-ops#598
---

**Centralize GitHub child-environment scrubbing.**

- Centralize reconciliation and forge credential child-environment filtering in a pure policy.
- Scrub credential, endpoint, debug, configuration, App-key, and caller-selected source names case-insensitively before setting the active `GH_TOKEN`.
- Preserve parent environments and token-free command inputs while adding hermetic parity coverage for both callers.
