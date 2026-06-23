---
slug: ce128-launch-runner-integration
ticket: ce-ops#128
type: added
scope: launch RunnerBackend integration
---

Wire backend-selected launches through `RunnerBackend.provision -> run` while
keeping the launched runner visible through the existing visibility surface.

- Adds a visible runtime bridge that binds the gVisor Docker/runsc runner argv
  to `VisibilityBackend.ensure_surface`.
- Replaces live `--backend gvisor` raw-tmux refusal with a fail-closed
  containerized launch path for `ce launch` and `ce lane launch`.
- Records runner runtime evidence in launch results and lane sidecars.
- Preserves fail-closed behavior when the requested backend is unavailable or
  cannot be composed with the v1 visibility surface.
