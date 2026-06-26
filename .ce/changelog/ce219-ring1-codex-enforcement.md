---
slug: ce219-ring1-codex-enforcement
ticket: ce-ops#219
type: fixed
scope: codex runsc governance
---

Closes the Codex Ring-1 containment wiring gap for managed runsc seats:

- Extends the managed Codex PreToolUse matcher to include `Read`, so
  credential-like path reads are gated by the shared hook policy.
- Embeds container-visible `CE_LEDGER_ROOT` and optional
  `CE_REVIEWER_AUTHORITY_REF` into the generated managed hook command for DGX
  and VPS Codex runsc seats.
- Preserves `allow_managed_hooks_only = true` and keeps the hook command
  credential-free.
- Adds focused regression coverage for restricted mechanic denial,
  credential-read denial without secret echo, out-of-manifest advisory allow,
  and permitted-action allow.
