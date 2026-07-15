---
slug: ce-552-systemd-execstart-defaults-day4
date: 2026-07-15
kind: fixed
scope: systemd gate daemons
issue: ce-ops#552
---

**Fix systemd daemon default expansion.**

- Move belt and ratifier interval defaults, plus the ratifier state-path default,
  into explicit non-secret systemd `Environment=` directives.
- Keep the deployment environment file as the override surface and document the
  ratifier defaults and required candidates path.
