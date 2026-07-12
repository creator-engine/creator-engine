---
slug: ce-538-hookpack-delivery
date: 2026-07-12
kind: fixed
scope: onboard claude hooks launch
issue: ce-ops#538
---

**Ship the tenant Claude hook-pack.**

- Packages the Claude hook scripts and settings template in the validator wheel.
- Materializes the hook-pack during fresh workspace onboarding without overwriting incompatible tenant settings.
- Preserves default Claude resume behavior when additional harness arguments are supplied.
