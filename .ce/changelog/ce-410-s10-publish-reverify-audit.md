---
slug: ce-410-s10-publish-reverify-audit
date: 2026-07-04
kind: fix
scope: conveyor
issue: ce-ops#410
---

**ce-ops#410 slice 10: final publish re-verification + per-phase audit.**

Part of ce-ops#410 (slice 10 — final slice before the Re-Arming Evidence Bundle)

Pre-existing checks preserved:
- Validation sandbox receipts record the daemon-owned worktree tree.
- Before publish, the landed branch tree is compared to the latest validation record tree.

Added checks:
- Publish-time landed head commit is re-derived from the repo checkout and compared to the landing result before tree identity is checked.
- Publish-time base ancestry is re-checked with `git rev-list --left-right --count`.
- Publish-time diff paths are parsed fail-closed from `git diff --name-status --find-renames` and compared to the per-PR carrier manifest.
- Checkout-local transport config is rejected for `core.hooksPath`, `credential.helper`, and `url.*.insteadOf`, including Git's lowercased `core.hookspath` and `url.*.insteadof` output.
- Allocation, validation, and publish phases emit structured audit logs without receipt nonce/signature leakage.
