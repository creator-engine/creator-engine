---
slug: ce-571-preflight-scratch-isolation
date: 2026-07-16
kind: fix
scope: validators
issue: ce-ops#571
---

**Isolate validate-pr scratch on disk-backed storage.**

- Run baseline and head pytest legs in one private `/var/tmp` scratch root.
- Keep that root's production prefix compact to avoid avoidable AF_UNIX path overflows.
- Remove only the completed invocation's owned scratch on every exit path.
- Keep unit coverage hermetic through an explicit scratch-parent test seam.
