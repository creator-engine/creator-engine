---
slug: ce-523b-jit-deflake
date: 2026-07-10
kind: fix
scope: Deflake test_live_cli_mismatched_peercred_rejects_jit_mint_without_credential — BrokenPipeError/ConnectionResetError race on AF_UNIX rejection path; tight 2s thread-join replaced with poll-with-deadline.
issue: 523
---

**test: deflake JIT peercred rejection race.**

The live-socket peercred rejection test was flaking under xdist load because the
server can check `SO_PEERCRED` and close the connection before the client's
`sendall` returns, causing a `BrokenPipeError` or `ConnectionResetError` that the
test treated as unexpected. Separately, a fixed 2 s `thread.join` deadline was too
tight on a loaded CI runner.

Fix: tolerate `BrokenPipeError`/`ConnectionResetError` on `sendall` as an expected
part of the AF_UNIX rejection path (the 403 response is already buffered), handle
EOF gracefully in the receive loop, and replace the `join(timeout=2)` with a
`_poll_until` helper that allows up to 30 s for the server thread to exit. The core
assertion — no credential minted, 403 returned, audit record correct — is
unchanged.
