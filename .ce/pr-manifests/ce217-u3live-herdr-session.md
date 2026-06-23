# PR path manifest — ce217-u3live-herdr-session · ce-ops#217 U3-live

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce217-u3live-herdr-session
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. The carrier lists itself.

Ratified gate:
ce-ops#217 U3-live herdr session API. CE drives the AGPL herdr binary only as a
separate subprocess/socket client; the control socket path is controller-owned
and never appears in governed seat env or ledger-visible terminal records.

The change:
Wire `HerdrSession.spawn_pane()` to the real `workspace create` root-pane
contract, run commands through `herdr pane run <pane_id> <command>`, wire
`send()` to `herdr pane send-text`, switch the herdr socket carrier to
`HERDR_SOCKET_PATH`, and update `observe()` to read raw stdout from `herdr pane
read --source recent --lines N --format text|ansi`.

Per-file purpose (the closed path-set — 6 paths):
- **`.ce/changelog/ce217-u3live-herdr-session.md`** *(A)* - per-PR changelog fragment.
- **`.ce/pr-manifests/ce217-u3live-herdr-session.md`** *(A)* - this carrier (self-inclusive).
- **`validators/creator_engine_validator/runner/herdr_session.py`** *(M)* - live workspace/run/send/read command helpers, `HERDR_SOCKET_PATH` carrier, and fail-closed governed env/socket handling.
- **`validators/tests/integration/test_herdr_live.py`** *(M)* - opt-in real-binary command-shape probe against `HERDR_LIVE_BINARY` or staged `/tmp/herdr-share/target/release/herdr`.
- **`validators/tests/unit/test_herdr_session.py`** *(M)* - mock subprocess coverage for spawn/run/send/read, malformed JSON, and controller-owned socket env.
- **`validators/tests/unit/test_visibility_backend.py`** *(M)* - terminal record/socket ownership assertion for the registered herdr backend.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=6389598e2a800bc6814d376bf09672b79385f0f1e0d2d97fb1fc91a43202f932

```text
.ce/changelog/ce217-u3live-herdr-session.md
.ce/pr-manifests/ce217-u3live-herdr-session.md
validators/creator_engine_validator/runner/herdr_session.py
validators/tests/integration/test_herdr_live.py
validators/tests/unit/test_herdr_session.py
validators/tests/unit/test_visibility_backend.py
```
