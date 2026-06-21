---
slug: ce180-brain-ingest-sqlite-gemma
ticket: ce-ops#180
type: feature
scope: brain recall ingest runtime and CLI
---

Adds the F6.2 brain recall ingest slice:

- Adds `ce brain ingest` for deterministic Markdown corpus discovery, chunking,
  content hashing, scoped `RecallChunk` construction, and idempotent vector-store
  upserts.
- Preserves offline CI behavior with the deterministic fake embedder by default;
  the `embeddinggemma` path requires an explicit local model path and adapter.
- Keeps confidential-scope protection fail-closed for egress-requiring embedders
  unless `--allow-confidential-egress` is supplied.
- Uses the Worker A/B store and Gemma modules dynamically when present, with a
  minimal private SQLite fallback for this slice's local/CI ingest tests.
