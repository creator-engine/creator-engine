---
slug: ce216-integrator-phase2-resolver
date: 2026-06-26
kind: added
scope: integrator llm resolver
issue: ce-ops#216
---

Adds the Phase-2 read-only LLM resolver for the Integrator.

- Introduces `IntegratorLlmResolver` that calls a mock/real LLM to produce
  deterministic resolution candidates for merge conflicts flagged by the
  Integrator runner.
- Wires the resolver into `IntegratorRunner` as an optional injection point;
  resolver is invoked only after deterministic paths have been exhausted.
- Keeps all LLM calls read-only: no file writes, no live-action authority.
- 192 unit tests covering resolver contract, runner integration, and
  fail-closed behavior when LLM is unavailable.
