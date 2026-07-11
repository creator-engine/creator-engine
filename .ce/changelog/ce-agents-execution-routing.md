---
slug: ce-agents-execution-routing
date: 2026-07-11
kind: docs
scope: AGENTS.md / fleet policy
issue: ce-ops#531
---

**Add execution-routing / no-inlining section to AGENTS.md.**

New section "Execution Routing — No Inlining" inserted between "Dispatch Discipline" and
"Hard-Stop Rules" in `AGENTS.md`. Covers two binding rules:

- **Bright-line delegation rule.** A controller turn is limited to: reading state,
  adjudication, brief composition, pointer sends, and single probes. Any unit needing more
  than ~3 mechanical tool calls (sweeps, harvests, preflights, cross-host recon, batch file
  ops, reviews) MUST be delegated to a spawned worker from `.claude/agents/`. Controller
  context is the factory's scarcest resource.

- **Wait-contract rules.** One-shot task agents may be awaited once. Persistent sessions
  (seats/foremen) MUST NOT be awaited — they never emit a completion signal; use pane reads
  between turns and durable READY signals. Two consecutive empty waits trigger liveness
  check + single re-dispatch or escalation. Finished subagents must be explicitly closed
  (slot hygiene).

**Why now.** SL-DAY arc evidence (2026-07-10 night) recorded in
`.ce/state/research/SL_DAY_LEDGER_20260711.md`: an inline wait-loop burned ~60 % of
controller context in a single turn before being caught. The wait-contract diagnosis
from that incident is now policy-level text so every agent session sees it at bootstrap.
Operator directive 2026-07-11, ce-ops#531 remedy b.
