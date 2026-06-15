---
slug: ce45-journey-cockpit
date: 2026-06-15
kind: added
scope: cockpit / CEO-mode journey
issue: ce-ops#45
---

**CEO-mode journey cockpit (ratified MINIMUM).**

Adds a solo-founder-facing journey surface to the existing Cockpit: a one-screen
`Frame -> Shape -> Build -> Review -> Ship` arc with an honest "you are here"
marker, plain-language Scope cards, a plain-language "what needs you" feed, and a
click/focus-to-detail explanation for every needs-attention item — none of which
assumes the reader is an engineer.

Built to the ratified L2/L3 hard law: all computation is a new pure projection
`snapshot["journey"]` in `runner/cockpit_readmodel.py` (arc, where-am-I priority,
Scope list, needs-attention translation of open decisions, deterministic detail
templates, and honest counters); the Textual view (`v3_cockpit.py`) only binds and
renders it via a `j` keybinding to a dedicated journey screen + a detail modal — it
computes nothing and reads no source (the L3 source guard is extended to cover it).

- Stage derives from conserved Scope state via `coordination.PHASE_BY_STATE` — no
  third vocabulary, no separate journey lifecycle.
- The expert ops board stays the **default** surface, un-demoted; this gate adds
  **no** mode switcher, persisted persona, default change, or autonomy control.
- Read-only: observation + explanation only — no approve/resolve/sync/dispatch/
  merge/push/write path.
- `ce cockpit --json` now carries the same `journey` data so a future GUI can
  replace the view alone. Plain-language copy guard enforced (zero blocked jargon
  in CEO-facing text). No new schema, runtime module, CLI command, or check.
