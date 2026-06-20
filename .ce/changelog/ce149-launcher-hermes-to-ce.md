---
slug: ce149-launcher-hermes-to-ce
date: 2026-06-20
kind: fixed
scope: ce launch / v3 state hygiene
issue: creator-engine/ce-ops#149
base: cbef5f36f45f41c596ad285222461396b24caaaf
---

Moves the live `ce launch` state defaults off the reserved `.hermes/` root and
onto the canonical `.ce/state` tree.

- Defaults the governed launch MCP config to
  `.ce/state/launch/<session>/mcp/ce-mcp.json`.
- Defaults lifecycle ledger registration to
  `.ce/state/active-work-ledger`.
- Updates top-level `ce launch`/`ce hud` help text while leaving the deferred
  v1 `.hermes` freeze intact.
- Extends v3 naming hygiene to scan the launch surface for `.hermes` residue
  and adds regression coverage for the planted-residue failure path.
