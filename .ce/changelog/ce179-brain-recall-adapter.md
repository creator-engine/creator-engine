---
slug: ce179-brain-recall-adapter
ticket: ce-ops#179
type: feature
scope: brain recall adapter runtime, schema, and offline tests
---

Adds the F6.1 substrate for the brain recall adapter slice:

- Defines the pluggable embedding and vector-store adapter spine, including a
  deterministic fake embedder and in-memory reference store.
- Defines `schemas/brain-recall-record.schema.yaml` for a derived recall index
  entry that points back to a Markdown source-of-truth file.
- Adds focused offline tests for schema validation, deterministic fake
  embedding, in-memory vector-store behavior, and the confidential-scope
  privacy gate for egress-requiring embedders.
- Keeps the vector store as a rebuildable projection; the schema rejects vector
  payloads as authoritative recall records.
