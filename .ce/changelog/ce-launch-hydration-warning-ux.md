---
slug: ce-launch-hydration-warning-ux
date: 2026-07-05
kind: tiny
scope: validators/creator_engine_validator/launch_runtime.py hydration-skip warning gating + tests + changelog
issue: canary-C UX gap (no ce-ops ticket)
---

**Hydration warning UX.**

- Declared work class: tiny.
- Suppressed the tenant-facing recall hydration warning when no embedding endpoint is explicitly configured (now logged at debug, not warning).
- Reworded the warning for a configured-but-unreachable embedding endpoint to state launch impact (recall quality reduced, launch proceeds) and remediation (fix the endpoint or unset the env var).
- Threaded a new `endpoint_configured` field through the recall status payload so `_emit_recall_status` can distinguish "unconfigured" from "configured but unreachable".
- Added unit coverage for the unconfigured (debug/no-warning) and configured-but-unreachable (warning-with-remediation) hydration paths.
