# PR path manifest — ce-337-self-push-service-parity

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`).
CI verifies this branch's base-to-head diff against the exact self-inclusive
path set below.

Declared work class: story

Scope: this bounded deployment-parity change repairs the canonical self-push
broker contract. The service uses the controller-managed stable broker checkout,
validates explicit peer identity and systemd activation before entering the
credential path, and the installer safely migrates the recognized stale dev-3
pathname binder. Focused hermetic tests and operator documentation cover the
fail-closed and idempotence contracts. No live deployment is performed.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=2ef87eb56189d3804442837725677bb36fb50d63ee29220a906720335e914a7f

```text
.ce/changelog/ce-337-self-push-service-parity.md
.ce/pr-manifests/ce-337-self-push-service-parity.md
deploy/systemd/README.md
deploy/systemd/ce-egress-broker.service
deploy/systemd/install-gate-daemons-systemd.sh
validators/tests/unit/test_gate_daemons_systemd.py
```
