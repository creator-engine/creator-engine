# PR path manifest - ce207-w2prime-pty-session - ce-ops#207 W2′ PTY-owned attachable session backend

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce207-w2prime-pty-session
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path set below
(including this carrier).

Base:
`4956994d1731185fa8fcf76c265caea250ad5cfe` (`origin/main` at branch creation).

Change:
ce-ops#207 work-unit **W2′** — the PTY-owned attachable-session backend + C1/C3
generalization, building on the W1 (#356) `VisibilityBackend` registry seam. CE now
owns the seat process under a **CE-held PTY** (`pty.fork`), not tmux, for the headless
visibility class. One owned session yields the evidence spine the launcher already
produces (Pane Registry record + `events.jsonl`); the PTY master tap EXISTS (held by
CE) but raw bytes are NOT streamed out — that is gated behind the separate W2-sec /
T1 lanes. A visibility-required **worker lane** can now launch with **no tmux** to a
schema-valid record + `events.jsonl` + a live PTY the substrate owns.

Per-file purpose:
- **`.ce/changelog/ce207-w2prime-pty-session.md`** *(A)* - changelog fragment for ce-ops#207 W2′.
- **`.ce/pr-manifests/ce207-w2prime-pty-session.md`** *(A)* - this carrier.
- **`validators/creator_engine_validator/seat_pty_session.py`** *(A)* - the CE-owned PTY session substrate: `spawn_pty_session` (`pty.fork` the sentinel-wrapped argv, parent keeps the master fd), `SeatPtySession` (pid + master_fd + reserved control-socket `surface_ref`), `socket_ref_for`. Owns the master tap; does NOT stream raw bytes anywhere (W2-sec/T1 own that).
- **`validators/creator_engine_validator/visibility_backend.py`** *(M)* - add `HeadlessVisibilityBackend` (`terminal_kind=headless`, `visibility_class=operator_inspectable`) spawning through `seat_pty_session`; add the `headless` kind + `SATISFYING_VISIBILITY_CLASSES`; extend `ensure_surface` with an optional `seat_dir`; register the headless backend.
- **`validators/creator_engine_validator/lane_runtime.py`** *(M)* - **C1**: generalize the visibility gate from "tmux only" to the attachable-and-emitting predicate (refuse an *unknown / non-satisfying* surface); add a `visibility_backend` injection seam; **C2**: scope the tmux-adapter wrap to `terminal_kind==tmux` and pass `seat_dir` to `ensure_surface` so `--no-tmux` routes to the headless backend.
- **`validators/creator_engine_validator/checks/pane_registry.py`** *(M)* - **C3** validator: generalize `_operator_visible_errors` → `_visibility_surface_errors` (tmux requires session/window/pane; headless requires `surface_ref`; reject an unknown visibility class or a class/kind mismatch).
- **`schemas/pane-registry.schema.yaml`** *(M)* - **C3** schema: add `headless` to `terminal.kind`, `operator_inspectable` to `visibility`, `surface_ref`/`pid` terminal properties, and a conditional requiring `surface_ref` for the headless kind.
- **`schemas/seat-lifecycle.schema.yaml`** *(M)* - add `headless` to the seat-lifecycle `terminal.kind` enum so `register_spawn` accepts the headless terminal record (the launcher copies the pane record's terminal kind into the lifecycle record).
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* - flip the `--no-tmux` help from "always refused" to "headless backend"; generalize the non-JSON launch success message so a headless record (no tmux pane ids) is described by kind + surface_ref + pid.
- **`validators/creator_engine_validator/_versions.py`** *(M)* - classify the new `seat_pty_session` module as `v1` (the v1 launcher's PTY-owning surface seam; imports only stdlib `os`/`pty`; both edges `v1->v1`, no new `shared->v1` ratchet edge).
- **`validators/tests/unit/test_seat_pty_session.py`** *(A)* - real-`pty.fork` tests proving CE owns a live PTY master over the seat (reads a marker off the master fd), applies seat env + cwd, exits 127 on failed exec, idempotent close.
- **`validators/tests/unit/test_visibility_backend.py`** *(M)* - headless backend registration, availability, headless terminal record, seat_dir requirement, and the no-new-byte-surface invariant.
- **`validators/tests/unit/test_lane_runtime.py`** *(M)* - the headline acceptance (a worker lane launches with NO tmux to a schema-valid headless record + `events.jsonl` + a live PTY); a deterministic fake-PTY record check; flip the former refuse-headless test to the unknown-kind refusal.
- **`validators/tests/unit/test_pane_registry.py`** *(M)* - headless record validates; missing `surface_ref` refused; class/kind mismatches refused.
- **`validators/tests/unit/test_ce_lane_cli.py`** *(M)* - flip the `--no-tmux` "always refused" test to assert `--no-tmux` now reaches LAUNCHED on the headless backend with no tmux spawned.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* - bump the `V1_RUNTIME` taxonomy-count assertion 25 -> 26 for the added `seat_pty_session` entry.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=16

AUTHORIZED_PATHS_SHA256=6d432907d22a31c36add2afbd07268fd3a7f706c53684ab65fbecfd4c8aca0d9

```text
.ce/changelog/ce207-w2prime-pty-session.md
.ce/pr-manifests/ce207-w2prime-pty-session.md
schemas/pane-registry.schema.yaml
schemas/seat-lifecycle.schema.yaml
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/checks/pane_registry.py
validators/creator_engine_validator/lane_runtime.py
validators/creator_engine_validator/seat_pty_session.py
validators/creator_engine_validator/visibility_backend.py
validators/tests/unit/test_ce_lane_cli.py
validators/tests/unit/test_lane_runtime.py
validators/tests/unit/test_pane_registry.py
validators/tests/unit/test_seat_pty_session.py
validators/tests/unit/test_version_boundary.py
validators/tests/unit/test_visibility_backend.py
```
