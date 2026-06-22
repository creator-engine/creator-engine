---
slug: ce-g9-brain-smoke
ticket: ce-ops#186
type: story
scope: G9 brain recall/hydrate smoke
---

Adds a bounded integration smoke for the G9 brain recall and session hydration
path:

- Builds a temporary Markdown corpus with brain hydration, merge queue review,
  seat topology/foreman, and decoy themes.
- Runs `ce brain ingest` and `ce brain recall --json` end to end with the
  deterministic offline embedder.
- Exercises the in-process recall surface and both CLI/in-process hydration
  paths, asserting recall pointers are present, CORE is reported but unchanged,
  and payload items do not inline source text.
