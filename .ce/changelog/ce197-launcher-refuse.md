---
slug: ce197-launcher-refuse
ticket: ce-ops#197
type: fixed
scope: launcher codex lifecycle
---

Fixes the Codex launcher path to resolve the harness before spawning and to
refuse missing binaries without creating stale seat state.

- Resolves Codex to an executable absolute path through the composed launch
  PATH or `CE_CODEX_HARNESS`.
- Refuses reused launched sentinel surfaces before wrapper materialization or
  tmux spawn.
- Reconciles sentinel exits into seat lifecycle records (`spent` for exit 0,
  `dead` for nonzero/127) with idempotent validation and atomic writes.
