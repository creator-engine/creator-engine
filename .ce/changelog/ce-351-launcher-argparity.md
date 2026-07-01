---
slug: ce-351-launcher-argparity
date: 2026-07-01
kind: fixed
scope: deploy / queue-daemon launcher (config/infra)
issue: ce-ops#351
---

**Fix arg-parity gap in queue-daemon relocation launcher — wire missing `--approval-wall-secret-ref-policy-sha`.**

- **`deploy/queue-daemon/launch-queue-daemon.sh`** — added `--approval-wall-secret-ref-policy-sha`
  arg (sourced from new required env var `CE_APPROVAL_WALL_SECRET_REF_POLICY_SHA`); added the
  var to `validate_required_env` and the usage/help block.  Without this arg the relocated VPS
  daemon would fail to fetch the approval-wall secret from OpenBao on cutover, silently blocking
  all auto-merges.
- **`deploy/queue-daemon/RELOCATION.md`** — added `CE_APPROVAL_WALL_SECRET_REF_POLICY_SHA` to
  the required-keys section of the cutover runbook so operators populate it in the env file.

No change to fail-closed logic, secret handling, or unrelated args.  The `--json` arg was
already present in the launcher; confirmed not missing.
