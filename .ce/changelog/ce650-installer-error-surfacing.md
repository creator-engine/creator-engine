---
slug: ce650-installer-error-surfacing
date: 2026-07-25
kind: fixed
scope: installer error reporting
issue: ce-ops#650
---

**Harden installer promotion refusal reporting.**

- Added a dedicated promoted-live-link verification exception, so both installer routes classify that controlled failure by type instead of matching diagnostic text.
- Kept the controlled promoted-link detail visible for remediation while withholding arbitrary promotion exception text from user-visible refusal results.
- Added message-independent coverage for type classification, rollback, and private generic-error reporting across the release and main-head routes.
