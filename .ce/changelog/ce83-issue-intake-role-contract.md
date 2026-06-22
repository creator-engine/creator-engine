---
slug: ce83-issue-intake-role-contract
date: 2026-06-22
kind: added
scope: GitHub issue intake contract
issue: ce-ops#83
---

Adds a documentation-only contract for the GitHub Issue intake role.

- Requires exact Operator authority before any issue mutation.
- Requires duplicate-search evidence and selection from existing repository
  labels only.
- Defines returned mutation evidence: issue URL, number, final body hash, final
  title, final labels, mutation time, actor identity when available, and the
  command or API surface used with credentials redacted.
- States that GitHub issues coordinate intent and do not authorize
  implementation.
