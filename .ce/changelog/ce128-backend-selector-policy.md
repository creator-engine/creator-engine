---
slug: ce128-backend-selector-policy
ticket: ce-ops#128
type: added
scope: launch runtime-policy backend selector
---

Add the SUB-A/SUB-D foundation seam for backend-selected launches.

- Adds `--backend {gvisor,openshell,local-noop}` to `ce launch` / `ce hud`
  and `ce lane launch`.
- Resolves the selected backend through the existing runtime-policy contract,
  with `gvisor` aliasing to the canonical `gvisor-proxy` policy key.
- Carries a sanitized launch-boundary runtime-policy stamp: policy identity,
  resolved backend, digest-pinned image, mount manifest, and egress allowlist.
- Refuses live launches for both explicit and resolved/default backend policies
  before raw tmux fallback until the RunnerBackend execution slice consumes the
  exposed stamp.
- Keeps the shared runtime-policy validator decoupled from v3 runner imports so
  the full examples sweep remains well-formed.
