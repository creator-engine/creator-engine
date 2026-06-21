---
slug: ce167-brain-assertion-ledger
ticket: ce-ops#167
type: feature
scope: validator brain assertion ledger
---

Adds the first Knowledge-SSOT assertion ledger slice:

- Defines `schemas/brain-assertion.schema.yaml` for structured, schema-gated,
  hash-chained brain assertion records.
- Adds `brain_runtime.py` plus `ce brain assert/check/correct/verify` under the
  CE local state root `.ce/state`.
- Adds the `ce_brain_assertions` validator check for schema, chain, tamper, and
  supersession validation.
- Covers assert/check, correction supersession, tamper detection, unknown
  checks, schema-invalid fail-closed behavior, and deterministic bytes in tests.

Out of scope by design: datastore, MCP server, recall/vector store, capability
probes, and MEMORY migration.
