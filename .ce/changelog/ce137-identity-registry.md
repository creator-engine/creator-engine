---
slug: ce137-identity-registry
date: 2026-06-26
kind: added
scope: identity registry SSOT
issue: ce-ops#137
---

- **Declared work class:** story

Adds a machine-readable GitHub identity and infrastructure registry schema and
a redacted example file for CE seat/account governance.

Public artifact = schema + redacted example only (creator-engine is a public
repo). The authoritative registry with real values is maintained internally.

- Added `docs/governance/identity-registry.example.yaml` as a schema-conformance
  sample with generic placeholders only (no real logins, App IDs, host IPs, or
  credential paths).
- Added `schemas/identity-registry.schema.yaml` to validate the registry shape
  while allowing `TODO_VERIFY` placeholders for unknown non-secret values.
- Wired the existing Validate workflow to schema-check the example file, proving
  schema + example conformance with zero real data exposed.
