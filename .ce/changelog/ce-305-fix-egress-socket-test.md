---
slug: ce-305-fix-egress-socket-test
date: 2026-06-27
kind: fixed
scope: validators / test robustness
issue: ce-ops#305
---

**fix(ce-ops#305): de-flake egress broker half-closed-client socket test**

- `validators/tests/unit/test_egress_host_broker.py`: replace the
  `socket_path.exists()` readiness poll in
  `test_serve_unix_socket_half_closed_client` with a `_connect_when_ready()`
  helper that retries `connect()` until the server is actually `listen()`-ing.
  The old gate passed after the server `bind()` (file appears on disk) but
  before `listen()`, so under `pytest -n auto` load a client could connect
  into the bind→listen window and get `ConnectionRefusedError` (Errno 111),
  intermittently failing the offline pytest gate on unrelated PRs.
