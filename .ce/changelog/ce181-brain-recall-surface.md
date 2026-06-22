---
slug: ce181-brain-recall-surface
ticket: ce-ops#181
type: feature
scope: brain recall surface (CLI/in-process hybrid recall + SSOT tiering + session hydration; MCP deferred to G11)
---

Adds the F6.3 company-brain recall surface as a CLI / in-process surface. The
standalone MCP recall surface is deferred to G11 (ce-ops#170 W4) and is NOT
delivered by this slice:

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
- Embedder/store parity fail-closed: recall exposes the same `--embedder` /
  `--model-path` selection as ingest and refuses up front when the selected
  embedder does not match the store — both on vector dimension AND on model
  identity (a same-dimension wrong-model query is still a different vector space).
  Ingest now persists the embedding `model_id` on the normal upsert path so this
  guard works for the standard ingest flow, not only `rebuild_from_source`.
- Builds on the merged F6.1 adapters (`brain_recall`) and F6.2 store/ingest
  (`brain_sqlite_vec`, `brain_ingest_runtime`); adds `SqliteVecStore.keyword_search`
  for the FTS5 leg and a new `brain_recall_surface` composing module. No new
  store/model/server work. The standalone MCP recall surface is deferred to G11
  (ce-ops#170 W4); this slice delivers CLI / in-process recall only. Offline,
  deterministic CI (heavy model deps blocked at import time).
