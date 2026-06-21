---
slug: ce182-pickup-feed-422-test-guard
date: 2026-06-21
kind: fixed
scope: belt pickup feed
issue: ce-ops#182
---

Hardens the offline pickup tests so the untyped-Search-query class of bug
(GitHub `HTTP 422: "Query must include 'is:issue' or 'is:pull-request'"`) can no
longer slip past the suite.

- The fake Search transport now asserts, on EVERY issued query, that the `q`
  carries exactly one `is:pull-request` / `is:issue` type qualifier — the offline
  stand-in for GitHub's real 422. Previously this check was per-test opt-in, which
  is why the live 422 shipped (ce-ops#182).
- Adds a regression test proving the fake transport rejects an untyped query.
- Test-only: the production query construction was already corrected on main.
