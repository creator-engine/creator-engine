---
slug: ce-supportagent-phaseb-model-wiring
date: 2026-06-29
kind: added
scope: validator support agent
issue: ce-ops#354
---

**Support agent Phase B model-backend wiring.**

- Wires `ce ask` through the provider-agnostic `CE_SUPPORT_AGENT_MODEL_CMD` command boundary.
- Adds privacy-preserving per-answer NDJSON usage logging under ignored instance state.
- Covers the full answer path with a stub model command, including cited answers, model refusals, and fail-closed unset command behavior.
