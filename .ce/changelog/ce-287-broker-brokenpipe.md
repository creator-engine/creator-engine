---
slug: ce-287-broker-brokenpipe
date: 2026-06-26
kind: fixed
scope: egress-broker / daemon robustness
issue: ce-ops#287
---

**fix(ce-ops#287): handle BrokenPipeError in egress broker Unix-socket daemon**

- `tools/egress-broker/egress_broker/host_broker.py`: wrap per-connection
  `sendall` in `try/except (BrokenPipeError, OSError)` so a half-closed
  client (probe/interrupt) cannot crash the accept loop.
- `validators/tests/unit/test_egress_host_broker.py`: add
  `test_serve_unix_socket_half_closed_client` covering the half-close path
  and verifying the daemon continues accepting after a bad client.
