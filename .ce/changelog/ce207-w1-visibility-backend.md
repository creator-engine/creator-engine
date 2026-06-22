---
slug: ce207-w1-visibility-backend
ticket: ce-ops#207
type: feature
scope: governed lane launch / visibility seam
---

Introduces a `VisibilityBackend` registry — the witnessability/surface seam —
modelled on the existing `RunnerBackend` registry, and routes the governed
lane-launch tmux spawn through it. Foundational, zero-behaviour-change slice
(W1) of the headless/non-tmux visibility work.

- Adds `visibility_backend.py`: a `VisibilityBackend` ABC plus a string-keyed
  registry (`register_visibility_backend` / `get_visibility_backend` /
  `available_visibility_kinds`) and a `SurfaceHandle` carrying the terminal
  record. The registry is kept separate from `RunnerBackend` because visibility
  composes orthogonally with the sandbox/runtime tier.
- Adds `TmuxVisibilityBackend`, a thin wrapper over the unchanged
  `tmux_adapter.TmuxAdapter` that reproduces today's tmux terminal record
  exactly (`operator_visible` + session/window/pane ids).
- Re-points the `lane_runtime.launch` tmux spawn seam through the registry,
  preserving the `tmux_adapter` injection kwarg so every existing fake-adapter
  test keeps working; the Pane Registry terminal record and visibility class are
  now built from the backend's `SurfaceHandle`.

No headless backend, no visibility-gate relaxation, no schema/validator change,
and no `ce launch` change in this slice — same inputs, same outputs, same
refusals.
