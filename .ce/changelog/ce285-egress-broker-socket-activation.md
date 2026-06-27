---
slug: ce285-egress-broker-socket-activation
date: 2026-06-27
kind: feat
scope: egress-broker
issue: ce-ops#285
work_class: story
---

**Add systemd socket activation for the egress broker sockets.**

The self-push broker now accepts one inherited Unix stream listener from systemd
(`LISTEN_FDS`/`LISTEN_PID`) through `socket.fromfd`, clears the activation
environment, and serves that already-listening socket without unlinking,
binding, chmodding, or replacing the socket path. The non-activated path keeps
the existing explicit bind behavior.

The self-review broker's `socketserver` wrapper now supports the same inherited
socket mode and skips path unlink cleanup when systemd owns the socket inode.

Adds paired `.socket` units for `/run/ce-egress/dev-3.sock` and
`/run/ce-egress/dev-3-review.sock`; the service units require/sequence after
those sockets, declare the socket units through `Sockets=`, and no longer use
`ExecStartPost` chown/chmod. Socket ownership and mode are now expressed in the
socket units. The systemd installer now renders the socket units before the
services so the new service dependencies are present when installed.

Review fixes preserved service parametricity: the services still pass
`$CE_EGRESS_BROKER_SOCKET` and `$CE_EGRESS_SELF_REVIEW_SOCKET` to the daemon
while the socket units own the default `/run/ce-egress/dev-3*.sock` paths.
Socket activation now also fails closed when `LISTEN_FDS` is present without a
matching integer `LISTEN_PID` for the current broker process.

Focused validation:

- `PYTHONPATH=tools/egress-broker:validators uv run --with pytest python -m pytest -q validators/tests/unit/test_egress_host_broker.py validators/tests/unit/test_egress_self_review_broker.py validators/tests/unit/test_egress_cli.py validators/tests/unit/test_egress_broker_daemon_vault.py validators/tests/unit/test_egress_review_daemon_vault.py`
- `PYTHONPATH=tools/egress-broker:validators uv run --with pytest python -m pytest -q validators/tests/unit/test_gate_daemons_systemd.py validators/tests/unit/test_egress_host_broker.py validators/tests/unit/test_egress_self_review_broker.py validators/tests/unit/test_egress_cli.py validators/tests/unit/test_egress_broker_daemon_vault.py validators/tests/unit/test_egress_review_daemon_vault.py`
- `git diff --check`
