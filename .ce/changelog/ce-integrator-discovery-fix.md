---
slug: ce-integrator-discovery-fix
date: 2026-06-24
kind: fixed
scope: validator engine (forge.integrator_belt)
issue: ce-ops#218
---

**Integrator daemon live PR-discovery fixes (ce-ops#218): make
`discover_daemon_candidates` work against the live GitHub GraphQL API.**

- Rename the search GraphQL variable `$query` → `$searchQuery`: the name `query`
  collided with `gh api graphql`'s reserved `query=` document field, so live
  candidate discovery failed closed before the daemon could evaluate any PR.
- Balance `_DAEMON_SEARCH_QUERY` braces (drop one stray trailing `}`): the
  document was malformed and rejected by the API parser.
- Add query-validity regression tests (brace-balance + no GraphQL variable named
  `query`). The prior unit tests injected `candidates=` and never exercised the
  live query construction, so CI was green while live discovery was broken — a
  live `--dry-run` smoke check is what surfaced both bugs.
