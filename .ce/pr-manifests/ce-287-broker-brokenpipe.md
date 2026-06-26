# PR path manifest — ce-ops#287 · egress broker BrokenPipeError fix

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-287-broker-brokenpipe
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below.
This carrier lists itself.

- **Declared work class:** tiny

Scope: ce-ops#287 — handle BrokenPipeError on half-closed clients in the egress
self-push broker daemon. One surgical fix to `serve_self_push_unix_socket` plus
a unit test for the half-close path.

Per-file purpose:
- **`.ce/changelog/ce-287-broker-brokenpipe.md`** *(A)* — changelog fragment.
- **`.ce/pr-manifests/ce-287-broker-brokenpipe.md`** *(A)* — this carrier (self-inclusive).
- **`tools/egress-broker/egress_broker/host_broker.py`** *(M)* — BrokenPipeError/OSError guard in `serve_self_push_unix_socket`.
- **`validators/tests/unit/test_egress_host_broker.py`** *(M)* — half-closed client test.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=fca1f45a87ee5bc4791d193bbda12fc1e2bf525607e5d3103076897e07ff1e5d

```text
.ce/changelog/ce-287-broker-brokenpipe.md
.ce/pr-manifests/ce-287-broker-brokenpipe.md
tools/egress-broker/egress_broker/host_broker.py
validators/tests/unit/test_egress_host_broker.py
```
