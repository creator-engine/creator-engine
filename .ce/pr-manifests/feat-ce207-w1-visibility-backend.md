# PR path manifest - ce207-w1-visibility-backend - ce-ops#207 W1 VisibilityBackend seam

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref feat/ce207-w1-visibility-backend
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path set below
(including this carrier).

Base:
`e76508b787f1fb755809d8214a6ea34fbb151a66` (`origin/main` at branch creation).

Change:
ce-ops#207 work-unit W1 — the foundational, zero-behaviour-change visibility seam.
Introduces a `VisibilityBackend` registry (mirroring the `RunnerBackend` registry
in `runner/backend.py`) kept separate from `RunnerBackend` because visibility (the
witnessability/surface tier) composes orthogonally with the sandbox/runtime tier.
Adds a thin `TmuxVisibilityBackend` that wraps the existing `tmux_adapter.TmuxAdapter`
unchanged and reproduces today's tmux terminal record exactly, then re-points the
C2 tmux spawn seam in `lane_runtime.launch` through the registry. No headless backend,
no C1 gate change, no schema/validator change, no `ce launch` change — same inputs,
same outputs, same refusals.

Per-file purpose:
- **`.ce/changelog/ce207-w1-visibility-backend.md`** *(A)* - changelog fragment for ce-ops#207 W1.
- **`.ce/pr-manifests/feat-ce207-w1-visibility-backend.md`** *(A)* - this carrier.
- **`validators/creator_engine_validator/lane_runtime.py`** *(M)* - route the C2 spawn seam through the visibility-backend registry (preserving the `tmux_adapter` injection kwarg); build the terminal record + visibility class from the backend's `SurfaceHandle`; preserve `LaunchResult.pane` via the handle's native object.
- **`validators/creator_engine_validator/visibility_backend.py`** *(A)* - new `VisibilityBackend` ABC + registry (`register_visibility_backend` / `get_visibility_backend` / `available_visibility_kinds`) + `SurfaceHandle` + `TmuxVisibilityBackend`.
- **`validators/tests/unit/test_visibility_backend.py`** *(A)* - registry ergonomics + proof the tmux backend reproduces the pre-seam terminal record exactly.
- **`validators/creator_engine_validator/_versions.py`** *(M)* - classify the new `visibility_backend` module as `v1` (the v1 launcher's witnessability/surface seam — a thin `tmux_adapter` wrapper consumed only by `lane_runtime`). Keeps both edges `v1->v1` so no new `shared->v1` ratchet edge is introduced; the `version_boundary` HARD/RATCHET invariants stay intact (no check weakening).
- **`validators/tests/unit/test_version_boundary.py`** *(M)* - bump the `V1_RUNTIME` taxonomy-count assertion 24 -> 25 for the added `visibility_backend` entry.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=3e1562415959b921b106c112f4877c26679c311bd03ad44876add237e2a42daf

```text
.ce/changelog/ce207-w1-visibility-backend.md
.ce/pr-manifests/feat-ce207-w1-visibility-backend.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/lane_runtime.py
validators/creator_engine_validator/visibility_backend.py
validators/tests/unit/test_version_boundary.py
validators/tests/unit/test_visibility_backend.py
```
