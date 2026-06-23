---
slug: ce219-codex-ring1-hookpack
ticket: ce-ops#219
type: added
scope: codex hooks launch
---

Adds CE's native Codex Ring-1 hook-pack path:

- Ships a managed Codex `requirements.toml` PreToolUse hook registration and
  repo-local hook shim.
- Bridges Codex PreToolUse JSON into the existing `creator-engine-validator
  hook-check` policy without forking policy logic.
- Refuses Codex launches before side effects when the managed hook-pack is not
  confirmed.
- Records Codex dispatches as `codex_managed_pretooluse`, while preserving
  containment and external forge/review/merge gates as backstops.
