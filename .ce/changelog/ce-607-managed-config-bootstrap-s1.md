---
slug: ce-607-managed-config-bootstrap-s1
date: 2026-07-18
kind: added
scope: managed configuration bootstrap
issue: ce-ops#607
---

**Managed configuration bootstrap S1.**

- Adds the managed configuration bootstrap implementation and its focused validator coverage.
- Declares the tmux adapter as runtime-plane because its authenticated local
  `AF_UNIX`/`SCM_RIGHTS` descriptor handoff preserves pinned-worktree FD
  ownership, with no permissive pathname or other weaker fallback.
