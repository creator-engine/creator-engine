---
slug: ce-383-conveyor-argv-hardening
date: 2026-07-03
kind: fix
scope: validators
issue: ce-ops#383
---

**Harden conveyor daemon argv ref handling.**

- Add a git push option terminator before daemon remote/refspec positionals.
- Reject unsafe base, remote, branch, landed branch, and PR base ref shapes before git/gh argv construction.
- Keep PR title/body as unrestricted free text in fixed gh flag-value slots.
- **Declared work class:** tiny
