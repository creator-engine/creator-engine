---
slug: ce-agent-model-pins
date: 2026-06-28
kind: chore
scope: agent governance
issue: ce-ops#N/A
---

**pin subagent models (reviewer/implementer/architect→sonnet, verification→haiku).**

- Pin model: sonnet on reviewer, implementer, and architect_research subagent definitions.
- Pin model: haiku on verification subagent definition.
- Prevents silent Opus inheritance when a controller dispatches these workers; enforces least-privilege model routing per spec-005 §d.2.
