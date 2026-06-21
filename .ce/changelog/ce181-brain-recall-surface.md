---
slug: ce181-brain-recall-surface
ticket: ce-ops#181
type: feature
scope: brain recall surface (hybrid recall + MCP/SSOT surface + session hydration)
---

Adds the F6.3 company-brain recall surface — MVP-complete after this slice:

- Adds `ce brain recall <context>` for hybrid retrieval: the sqlite-vec semantic
  leg fused with the FTS5 keyword leg (the column F6.2 populated but never
  queried) via reciprocal-rank fusion. Returns top-K records as pointers
  (`source_path`/`chunk_ref`/`content_hash`/`as_of`) — never inlined content — so
  the agent re-verifies against the live Markdown source-of-truth.
- Exposes recall on the SAME brain surface as the Knowledge-SSOT, tier-tagged:
  verifiable SSOT assertions (`tier=ssot`) always take structural precedence over
  probabilistic recall hits (`tier=recall`); no second surface is stood up.
- Adds `--hydrate` session hydration: injects a top-K, context-relevant recall
  slice alongside an unchanged always-load CORE markdown — additive over today's
  flat-file memory (the CORE file is reported, never read or mutated), fixing the
  "entry below the MEMORY.md cut never loads" and "durable != discoverable" gaps.
- Privacy fail-closed: the semantic leg refuses to embed a query through an
  egress-requiring embedder over a confidential corpus without explicit consent,
  reusing the F6.1 gate; the local-first default embedder needs no consent.
- Builds on the merged F6.1 adapters (`brain_recall`) and F6.2 store/ingest
  (`brain_sqlite_vec`, `brain_ingest_runtime`); adds `SqliteVecStore.keyword_search`
  for the FTS5 leg and a new `brain_recall_surface` composing module. No new
  store/model/server work (Phase-2). Offline, deterministic CI (heavy model deps
  blocked at import time).
