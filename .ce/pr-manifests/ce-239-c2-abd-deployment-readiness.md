# PR path manifest — ce-ops#239 — C2-A/B/D deployment readiness

Work class: `story`.

This carrier keeps the approval wall dormant: it records only environment-driven
deployment coordinates and operator documentation. It contains no secret or
policy value, live environment/service action, wall-state change, or arming act.
ce-ops#554 lease-restart work is deliberately separate.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=71530f7fe809bd0d7c5e90b6d6f176f40aa3632e437863bff68637c9a453ebf9

```text
.ce/changelog/ce-239-c2-abd-deployment-readiness.md
.ce/pr-manifests/ce-239-c2-abd-deployment-readiness.md
deploy/systemd/README.md
deploy/systemd/ce-integrator-daemon.service
deploy/systemd/install-gate-daemons-systemd.sh
validators/tests/unit/test_gate_daemons_systemd.py
```
