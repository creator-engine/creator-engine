---
slug: ce-brain-eval-harness
date: 2026-06-28
kind: added
scope: brain recall eval
issue: ce-ops#79
---

**Added an offline brain recall eval harness.**

- Added `brain_eval.py`, a deterministic golden-set harness over representative
  controller-context queries and fixture Markdown snippets.
- Added `ce brain eval`, wired only through the existing brain command group, to
  print a human summary or structured JSON with per-leg recall@K metrics.
- Added unit coverage for report shape, deterministic reruns, custom K values,
  and the CLI JSON/human paths.

The harness is pure offline: no vLLM, network, or live endpoint is used.
