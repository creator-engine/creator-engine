# CE v3 — The Cockpit (post-pilot graduation surface)

*Curated design sketch (provenance: 2026-06-08 design session). **DESIGNED / post-pilot graduation — NOT a G-7 or pilot deliverable.** Pilot G-7 ships the agent-native TUI; the cockpit is the named next surface. Execution status lives in [`docs/v3-roadmap.md`](../v3-roadmap.md). Vocabulary canon: [`stage-vocabulary.md`](./stage-vocabulary.md).*

## What the cockpit is

The cockpit is the **graduation of the agent-native TUI into a dedicated mission-control surface where CE owns the screen.** The framing: *PTY makes CE a wrapper around someone else's terminal; ACP makes CE a **cockpit**.* The pilot rides **inside** the developer's own agent (one agent, conversational). The cockpit exists for **scale** — a fleet of Scopes in flight, where a chat TUI no longer suffices and you need a board.

## The shape (mission-control / fleet board)

- **The board = the stages.** Columns are `Frame · Shape · Build · Review · Ship`; cards are **Scopes**; the board *is* the kanban projection (state-as-artifacts, not a new state machine). You see the whole fleet's state at a glance — the **same five words**, re-rendered as lanes.
- **CE owns the screen.** Runs are headless (boxed; ACP where available, hooks otherwise). Every agent permission-request routes through `classify()` → **auto-allow / auto-deny / escalate**. Only **escalations + your bet-ratifications + your reviews** surface. The human is a **mission controller** working a queue of "things that need you" — not a babysitter watching panes.
- **The meters, scaled up.** The unified context+spend status line becomes a **fleet cost meter** + per-run budgets — the tokenomics dashboard. Deny-by-default blast-radius and "never bet the farm" made *visible*; the cost axis is a first-class instrument.

## Transport

ACP is what *enables* owning-the-screen (headless agents streaming typed events). The pilot uses the subprocess + CC-hooks transport; the cockpit **leans into ACP** where the vendor's terms permit it, and **degrades to the hooks transport** otherwise. CE never bets the farm on ACP — the binding authority is always CE's external gate, never the in-agent hook. (See the substrate decision in the v3 architecture corpus.)

## Graduation, not replacement (the load-bearing property)

The cockpit is the **same language, same artifacts, re-rendered.** The stage phases (`Frame → Ship`); the Scope card (`Goal · Done-when · Budget · Change-type · Ready`); the ◆ CE Completion Report (`Outcome · Verdict · Next`); and the Scope · ratification · evidence-chain · manifest · outcome · spend artifacts — all carry over verbatim, re-rendered visually from the TUI onto the board. A developer who learned the agent-native TUI already knows the cockpit. That is what makes it a *graduation path* and not a second product.

## Pairs with CEO mode

The cockpit is the natural home of **CEO mode** — the eager end of the detect-and-offer dial, a fleet over a ratified backlog, machine-readable objectives as the goal layer. **Dev mode** = one agent in your own TUI; **CEO mode** = a fleet on the board. The eagerness dial `f(persona, risk-class)` (see [`shaping-ux.md`](./shaping-ux.md)) is exactly the knob that scales between them. CEO mode itself is deferred post-pilot.

## Non-goals

- **Post-pilot, build-deferred.** Pilot G-7 ships the agent-native TUI; the cockpit, the ACP/Tier-A adapter, CEO mode, and the durable Skill axis are the named post-pilot arc. This document is the design anchor so the pilot surface doesn't paint the cockpit into a corner — same words, same artifacts, board-ready.
