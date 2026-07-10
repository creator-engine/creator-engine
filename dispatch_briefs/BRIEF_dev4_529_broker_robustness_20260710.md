# DISPATCH — dev-4 — 2026-07-10 — unit: egress-broker refusal robustness — class S
Role: implementer foreman. Signal: `SELF-PUSHED <branch> <sha> PR=<number>`
or `READY-FOR-HARVEST <branch> <sha>` (fallback — see Signal section below)
or `BLOCKED <branch> <one-line-reason>`.
Branch `ce-529-broker-refusal-robustness` off freshly fetched origin/main OR LATER. Worktree
/var/tmp/wt-ce-529-broker-refusal-robustness. Standing preflight directive: run
`ce validate-pr --profile contained-seat` if your environment can; else focused tests +
BLOCKED(env) per protocol. PRE-SIGNAL CHECKLIST: focused tests green + confidentiality check:
`python -m pytest validators/tests/unit/test_public_docs_confidentiality.py::test_tracked_text_files_contain_no_new_confidential_or_internal_references -q`

## Context (embedded)

The self-push egress broker daemon exits on request-handling errors instead of answering the
client. Three error classes have been observed to crash the live daemon (exit code 2), each
triggering restart backoff and invalidating connected seats' socket binds:

1. **Empty or aborted client connection** — a seat that connects and immediately closes (probe,
   interrupt, or half-open socket) can produce `ConnectionResetError` or `OSError` from the
   per-connection recv loop. The exception escapes unhandled up through the accept loop and into
   `main()`, which exits the process.

2. **Mint-layer configuration error (`ForgeConfigError`)** — during the apply path, if the
   installation token mint step raises `ForgeConfigError` (e.g. a forge transport failure or
   misconfigured App credentials), the exception escapes `handle_self_push_request`, which only
   catches `EgressRefused`, and propagates to `main()`, causing exit 2.

3. **Policy/guard push refusal (`PushRefused`)** — `change_push.push_change` raises `PushRefused`
   (a subclass of `ForgeConfigRefused` → `ForgeConfigError`) when the broker's supersession guard
   or non-fast-forward check denies a push. This is a normal policy outcome; it must produce a
   structured 403 response to the client, not a daemon exit.

All three classes reproduced live on 2026-07-10. The correct behaviour at each is: catch at the
per-request boundary, write a structured JSON response, and continue accepting. Client disconnects
are logged and ignored; no response is attempted. Startup and config-file errors remain
fail-closed at boot — only per-request error handling changes.

Note: the `BrokenPipeError`/`OSError` guard around `sendall` in the reject-peer path and the
response path already exists in the accept loop (a prior fix). This unit does not redo that work;
it closes the recv-phase and request-handling gaps those sendall guards do not cover.

## Unit

Read the three broker modules to locate the structures below before writing any code.

**`tools/egress-broker/egress_broker/orchestrator.py` — `courier` function, push block:**

The `courier` function's apply path (step 6) runs `_push(token)` inside a `try/finally` whose
`finally` always revokes the token. `PushRefused` from `change_push.push_change` is NOT caught
in that block; it propagates out of `courier` with the token already revoked (the `finally` ran)
but without an audit record or structured response. Fix: inside the `try` of the push/PR block
(after `push_result = _push(token)` but before the `finally`), add an `except PushRefused as exc`
clause that audits a deny record (reusing the `_base_record` pattern and `append_audit` already
used by the deny path above it) and raises `EgressRefused` wrapping the `PushRefused` message and
the deny audit record. Import `PushRefused` from
`creator_engine_validator.forge.change_push` (it is already importable from that module). This
converts a policy guard refusal into the well-defined `EgressRefused` path, which the host broker
already turns into a 403 `egress_refused` response. Do NOT catch `ForgeConfigError` here — that
class represents a transport/internal failure and must propagate to the request boundary for 500
mapping.

**`tools/egress-broker/egress_broker/host_broker.py` — two sites:**

Site 1 — `handle_self_push_request`, courier call block (the `try/except EgressRefused` around
`courier_fn(...)`): add a second `except` clause after the existing `except EgressRefused`:

```python
except ForgeConfigError as exc:
    response = {
        "status": 500,
        "reason": "broker_internal_error",
        "error_class": type(exc).__name__,
    }
    return _assert_response_secret_free(response)
```

Import `ForgeConfigError` from `creator_engine_validator.forge.github_repo_config` at the top of
the file (check whether it is already imported before adding). This catches transport and internal
mint failures at the request boundary and returns a 500-class JSON, keeping the daemon alive. Do
NOT import or catch `PushRefused` here — after the `orchestrator.py` fix above, `PushRefused` now
travels through `EgressRefused` and hits the existing `except EgressRefused` handler.

Site 2 — `serve_self_push_unix_socket`, accept loop body, recv section and json-line call: the
inner recv `while True` loop and the `handle_self_push_json_line` call are currently bare. Wrap
both in a single `try` block covering from the recv loop through (but not including) the response
`sendall` call:

```python
try:
    data = b""
    while True:
        chunk = conn.recv(65536)
        if not chunk:
            break
        data += chunk
        if b"\n" in data:
            break
    line = data.decode("utf-8", errors="replace").splitlines()[0] if data else ""
    response = handle_self_push_json_line(line, ...)
except (BrokenPipeError, ConnectionResetError, OSError) as exc:
    print(
        f"[ce-egress-self-push] client disconnect during recv: {type(exc).__name__}; "
        "dropping connection",
        file=sys.stderr,
    )
    if once:
        break
    continue
except Exception as exc:  # noqa: BLE001
    print(
        f"[ce-egress-self-push] unhandled request error: {type(exc).__name__}; "
        "answering 500 and continuing",
        file=sys.stderr,
    )
    response = json.dumps(
        {"status": 500, "reason": "broker_internal_error", "error_class": type(exc).__name__},
        sort_keys=True, separators=(",", ":"),
    ) + "\n"
```

The `try/except` structure must preserve the existing `once` and `continue` semantics of the
surrounding loop. The bare `except Exception` is deliberately broad at the process boundary: the
daemon must survive every per-request failure. Do NOT redact or log `str(exc)` for the broad
catch — `type(exc).__name__` only, for the same reason as the existing `main()` handler.

**`tools/egress-broker/ce_egress_self_push_broker.py` — no changes required** unless the imports
or structure of `main()` must be adjusted to remain consistent with the host_broker changes above.
Startup and config-file errors (`BrokerConfigError`, `_BrokerStartupError`, `EgressSignerError`)
still exit fail-closed at boot via the existing pre-serve try/except blocks; that behaviour must
not change.

**Check for an unlanded branch whose slug contains `broker-brokenpipe`:** look in the local
worktree's git log and any `.ce/pr-manifests/` or `.ce/changelog/` entries matching that slug. A
prior branch `ce-287-broker-brokenpipe` addressed only the `sendall`-phase `BrokenPipeError` (the
fix is already in main — visible in the `serve_self_push_unix_socket` sendall try/except blocks).
Its intent is already incorporated. Implement fresh on current main; do not re-open that work.

**Tests — `validators/tests/unit/test_egress_host_broker.py` and
`validators/tests/unit/test_egress_orchestrator.py`:**

Add focused tests for each of the four cases below. All tests must use in-test server instances
(threading or direct function calls); never point any test client at the real broker socket
`/run/ce-egress-broker.sock`. The live broker crashes on malformed requests until this fix lands.

- **Empty connection test** (`test_serve_unix_socket_empty_connection_continues`): start a
  `serve_self_push_unix_socket` thread with `once=False`; connect with `AF_UNIX`, send nothing,
  close immediately; then connect again with a valid request and assert a well-formed response is
  received. The daemon must handle both connections without exiting.
- **Mid-request disconnect test** (`test_serve_unix_socket_mid_recv_disconnect_continues`):
  connect, send a partial (no newline) payload, and close. Verify the daemon does not exit and
  continues accepting on a second connection.
- **PushRefused → 403 + loop alive** (`test_serve_unix_socket_push_refused_returns_403`): inject
  a `courier_fn` that raises `PushRefused("non-fast-forward")`. Assert the response is
  `{"reason": "egress_refused", "status": 403, ...}` and the daemon continues accepting.
- **ForgeConfigError → 500 + loop alive** (`test_serve_unix_socket_forge_config_error_returns_500`):
  inject a `courier_fn` that raises `ForgeConfigError("mint failed")`. Assert the response has
  `"status": 500` and `"reason": "broker_internal_error"` and the daemon continues accepting.

Do not weaken, remove, or skip any existing test in `test_egress_host_broker.py`,
`test_egress_orchestrator.py`, or `test_egress_cli.py`. Extend only.

## Files (allowed writes)

Exactly the files that actually need the boundary change from the analysis above:
- `tools/egress-broker/egress_broker/orchestrator.py` — `PushRefused` catch + `EgressRefused` wrap in `courier` push block
- `tools/egress-broker/egress_broker/host_broker.py` — `ForgeConfigError` catch in `handle_self_push_request`; recv/json-line try/except in `serve_self_push_unix_socket`
- `tools/egress-broker/ce_egress_self_push_broker.py` — only if import or consistency changes are required by the above; otherwise leave untouched
- `validators/tests/unit/test_egress_host_broker.py` — four new focused tests
- `validators/tests/unit/test_egress_orchestrator.py` — if the `PushRefused` → `EgressRefused` wrapping in `courier` warrants a direct orchestrator-level test
- `.ce/changelog/ce-529-broker-refusal-robustness.md` — changelog fragment
- `.ce/pr-manifests/ce-529-broker-refusal-robustness.md` — carrier (slug=branch) with exactly `- **Declared work class:** S`

Product lens throughout. No internal ticket references anywhere in committed content.

## Stop lines

`tools/mint-broker/**`, `egress_broker/policy.py` decision logic (response mapping changes only —
do not touch the pure `evaluate` function or any `Decision`/`Precondition` dataclass),
`validators/**` outside the broker test modules named above, `deploy/**`, `ce_cli.py`,
`v3_cli.py`, `docs/**`, `.ce/brain/assertions.yaml`.

## Signal

After focused tests pass and the confidentiality check is green:

1. Commit all changes on branch `ce-529-broker-refusal-robustness`.
2. Push through the broker socket by running, inside the container:
   ```
   python3 /var/tmp/canary.py --repo /workspace/creator-engine --branch ce-529-broker-refusal-robustness
   ```
   The canary client is the push client: it pushes the branch and opens the PR via the live
   broker socket.
3. On success, signal: `SELF-PUSHED ce-529-broker-refusal-robustness <full-40-hex-sha> PR=<number>`

**Fallback:** if the broker socket is unreachable or the push fails with a non-policy error
(socket not found, transport failure, unexpected 500), signal:
`READY-FOR-HARVEST ce-529-broker-refusal-robustness <full-40-hex-sha>` and include the failure
class (e.g. `socket-unreachable`, `transport-500`) on the next line so the controller can triage.
A 403 `egress_refused` policy refusal is NOT a fallback trigger — resolve it (check that the
branch is freshly based on origin/main and carries both its changelog and its carrier).

**Supersession guard warning:** the broker's supersession check requires the branch to be freshly
based on current origin/main AND to carry the `.ce/changelog/ce-529-broker-refusal-robustness.md`
and `.ce/pr-manifests/ce-529-broker-refusal-robustness.md` files. A stale base or missing carrier
causes a policy-level 403 push refusal. Fetch origin and rebase before running the canary if any
doubt exists about the merge base.

**Safety warning:** while developing and running the new tests, NEVER point a test client at the
real live broker socket `/run/ce-egress-broker.sock` with malformed or test requests. Until this
fix lands, any unhandled exception from a malformed request crashes the live broker and triggers
restart backoff, affecting all connected seats. All four new tests must use in-test server
instances (thread-started `serve_self_push_unix_socket` with a temp socket path, or direct
function calls). Use `tmp_path` fixtures for socket paths.
