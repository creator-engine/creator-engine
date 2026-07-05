---
slug: ce-451-surfaces-checker-hardening
date: 2026-07-05
kind: fix
scope: validators
---

**Harden the surfaces manifest consistency checker.**

- Treat literal `UNSET` digests as unpinned unless covered by the current CE seat image debt allowlist.
- Ratchet the CE seat image placeholder so pinning the digest requires removing the allowlist entry.
- Replace substring Dockerfile image matching with exact aliases and explicit image overrides.
