---
slug: ce614-policy-pair-dirfd-anchor
date: 2026-07-22
kind: security
scope: runtime-policy pair commit directory anchoring
issue: ce-ops#614
work_class: XS
---

**security(runtime-policy): anchor pair mutation to the validated directory.**

- Pins the validated runtime-policy parent directory for staging, backup links,
  replacement, rollback/recovery renames, cleanup, and directory sync. Every
  pair entry is addressed by basename through that descriptor.
- Refuses before destination creation when the host lacks the required dirfd
  primitives, and preserves existing no-follow, private-mode, fail-closed, and
  typed recovery behavior.
- Adds hermetic directory-swap and symlink-parent threat tests proving the
  commit cannot write its policy or receipt pair through a replacement parent.
