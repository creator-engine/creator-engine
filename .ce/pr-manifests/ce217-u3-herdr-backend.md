# PR path manifest - ce217-u3-herdr-backend

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce217-u3-herdr-backend
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below (the carrier lists itself); the repo-wide fidelity scan requires the
declared count and SHA256 to match the fenced block.

Ratified gate:
Operator-ratified 2026-06-23 - Cockpit-on-herdr build, ce-ops#217, Posture A
(AGPL-3.0 source-available fork). Design-of-record:
`.ce/state/research/DESIGN_COCKPIT_ON_HERDR_20260623.md`.

Base:
`3088f622beacaba9bb415eabf54e481e03250ff8` (`origin/main`).

The change:
U3 wires a live `terminal_kind=herdr` `VisibilityBackend` over the herdr socket,
keeps CE Python and herdr Rust separated by subprocess/socket boundaries, retires
the #368 `pty.fork` backend path, and preserves the §7 invariant that the herdr
control socket is owned by the CE substrate/controller and never handed to the
governed seat.

Per-file purpose (the closed path-set - 20 paths):
- **`.ce/changelog/ce217-u3-herdr-backend.md`** *(A)* - per-PR changelog fragment.
- **`.ce/pr-manifests/ce217-u3-herdr-backend.md`** *(A)* - this carrier (self-inclusive).
- **`schemas/pane-registry.schema.yaml`** *(M)* - add `terminal.kind: herdr` and require `surface_ref`, `pane_id`, and `pid`.
- **`schemas/seat-lifecycle.schema.yaml`** *(M)* - allow herdr terminal records and their socket/pid identity fields.
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* - add bounded `--terminal-kind herdr` selection and retire the old no-tmux headless PTY route.
- **`validators/creator_engine_validator/checks/pane_registry.py`** *(M)* - accept herdr as an `operator_inspectable` backing surface.
- **`validators/creator_engine_validator/lane_runtime.py`** *(M)* - route non-tmux inspectable launch through the registry with pre-side-effect availability refusal.
- **`validators/creator_engine_validator/runner/herdr_session.py`** *(M)* - live subprocess/socket client for workspace, pane split/run/read, and wait agent-status; `send()` remains fail-closed for U4.
- **`validators/creator_engine_validator/seat_lifecycle.py`** *(M)* - preserve herdr `surface_ref` and `pid` in seat-lifecycle terminal records.
- **`validators/creator_engine_validator/seat_pty_session.py`** *(M)* - retire the #368 PTY byte-tap spawn path.
- **`validators/creator_engine_validator/visibility_backend.py`** *(M)* - register `HerdrVisibilityBackend` and stop registering the retired headless backend.
- **`validators/tests/integration/test_herdr_live.py`** *(A)* - optional live herdr probe, skipped when the durable binary is absent.
- **`validators/tests/unit/test_ce_lane_cli.py`** *(M)* - CLI regression coverage for retired headless and herdr terminal selection.
- **`validators/tests/unit/test_herdr_session.py`** *(M)* - mocked subprocess/socket unit coverage for the herdr client.
- **`validators/tests/unit/test_lane_runtime.py`** *(M)* - herdr launch record contract coverage.
- **`validators/tests/unit/test_pane_registry.py`** *(M)* - herdr schema/local predicate coverage.
- **`validators/tests/unit/test_seat_lifecycle.py`** *(M)* - lifecycle preservation of herdr terminal identity.
- **`validators/tests/unit/test_seat_pty_session.py`** *(M)* - #368 PTY retirement regressions.
- **`validators/tests/unit/test_seat_reaper.py`** *(M)* - explicit U3 reaper behavior for herdr seats (escalate until a reviewed close executor lands).
- **`validators/tests/unit/test_visibility_backend.py`** *(M)* - herdr backend registration, record shape, read/wait delegation, and §7 overlap refusal.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=20

AUTHORIZED_PATHS_SHA256=ec90821e37928c96004a1d00b7ab3760d8dec5fdde4d7e97131c3a80fe6e1e8e

```text
.ce/changelog/ce217-u3-herdr-backend.md
.ce/pr-manifests/ce217-u3-herdr-backend.md
schemas/pane-registry.schema.yaml
schemas/seat-lifecycle.schema.yaml
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/checks/pane_registry.py
validators/creator_engine_validator/lane_runtime.py
validators/creator_engine_validator/runner/herdr_session.py
validators/creator_engine_validator/seat_lifecycle.py
validators/creator_engine_validator/seat_pty_session.py
validators/creator_engine_validator/visibility_backend.py
validators/tests/integration/test_herdr_live.py
validators/tests/unit/test_ce_lane_cli.py
validators/tests/unit/test_herdr_session.py
validators/tests/unit/test_lane_runtime.py
validators/tests/unit/test_pane_registry.py
validators/tests/unit/test_seat_lifecycle.py
validators/tests/unit/test_seat_pty_session.py
validators/tests/unit/test_seat_reaper.py
validators/tests/unit/test_visibility_backend.py
```
