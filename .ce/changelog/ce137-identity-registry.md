---
slug: ce137-identity-registry
date: 2026-06-26
kind: added
scope: identity registry SSOT
issue: ce-ops#137
---

- **Declared work class:** story

Adds a non-secret, machine-readable GitHub identity and infrastructure registry
for CE seat/account governance.

- Added `docs/governance/identity-registry.yaml` with accounts, apps, tokens,
  signing-key custody pointers, host topology, and author/reviewer matrix data.
- Added `schemas/identity-registry.schema.yaml` to validate the registry shape
  while allowing `TODO_VERIFY` placeholders for unknown non-secret values.
- Wired the existing Validate workflow to schema-check the identity registry.
