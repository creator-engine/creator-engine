---
slug: ce45-journey-cockpit-elevation
date: 2026-06-20
kind: changed
scope: cockpit / CEO-mode journey
issue: ce-ops#45
---

**Journey cockpit elevation — the founder journey is now the DEFAULT face.**

Supersedes the PR #230 "ratified minimum" (which explicitly punted the default
change and mode switch). The solo-founder journey is now the cockpit's default
face and the expert ops board is demoted to a **Dev** face you switch to.

- **Journey = default face; Dev board = a switch-to face.** `CockpitApp` installs
  the persona's face (each is a Textual mode with its own screen stack), with a
  CEO ↔ Dev switch (`d` / `c`). The persona is **persisted** as a per-instance UI
  preference under `<root>/cockpit/prefs.json`.
- **Full visual development-arc / roadmap.** The journey shows a one-screen picture
  of the CE process: the five-stage progress strip with a plain "Step N of 5"
  position, and a lane per `Frame → Shape → Build → Review → Ship` stage carrying a
  plain description and the project's work sitting in it (the visual project arc),
  with the current stage marked.
- **First-class decision-inbox.** "What needs you" is a prominent, bordered, titled
  surface (not a sub-panel) whose accent turns gate-red when work needs the founder
  and spark-green when the queue is clear; click/focus opens a plain, non-engineer
  explanation per item.

Built to the ratified L2/L3 hard law: all new computation is additive pure data on
`snapshot["journey"]["arc"]` (`stage_descriptions`, `lanes`, `position`,
`journey_lane_count`) in `runner/cockpit_readmodel.py`; the Textual view
(`v3_cockpit.py`) only binds and renders it. The persona is a UI **preference**,
not governance state: it lives in a new textual-free `runner/cockpit_prefs.py`
(pure normalize/fold + a tolerant I/O edge), is read by the composition root
(`v3_cli._cmd_cockpit`) and injected into the view with an `on_persona_change`
callback — so the L3 view performs no file I/O and the L3 source guard stays green.

- Stage derives from conserved Scope state via `coordination.PHASE_BY_STATE` — no
  third vocabulary, no separate journey lifecycle.
- Read-only: observation + explanation only — no approve/resolve/sync/dispatch/
  merge/push/write path (the interactive write-seam is a separate, governance-
  reviewed slice).
- `ce cockpit --json` carries every new `journey.arc` datum (the future-GUI parity
  seam); the persona preference is deliberately **not** in the snapshot. Plain-
  language copy guard enforced (zero blocked jargon in CEO-facing text, including
  the new stage descriptions and roadmap lanes).
