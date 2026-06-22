---
slug: ce211-node24-actions
ticket: ce-ops#211
type: fix
scope: github actions runtime pins
---

Updates the GitHub Actions workflow pins that were still running deprecated
Node 20 action builds under forced Node 24 compatibility.

- Bumps `actions/checkout` in `validate.yml` and `ce-ops-autoclose.yml` to the
  current Node 24-capable `v5` tag target while preserving full SHA pinning.
- Bumps `actions/setup-python` in `validate.yml` to the current Node 24-capable
  `v6` tag target while preserving full SHA pinning.

No workflow triggers, permissions, scripts, or validator behavior are changed.
