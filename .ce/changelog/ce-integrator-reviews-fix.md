---
slug: ce-integrator-reviews-fix
date: 2026-06-24
kind: fixed
scope: validator engine (forge.integrator_belt)
issue: ce-ops#218
---

**Integrator daemon: read approvals from `latestOpinionatedReviews`, not
`latestReviews` (ce-ops#218).**

- GitHub's `latestReviews` GraphQL field is empty for a reviewer who was not
  formally *requested* (e.g. a controller running `gh pr review --approve`), so
  the daemon's `approving_review_commits` came back empty and it skipped every
  genuinely-approved PR with `approval_not_current_head` — never merging anything.
- Switch `_DAEMON_SEARCH_QUERY` + `_parse_daemon_pr` to `latestOpinionatedReviews`
  (latest APPROVE / REQUEST_CHANGES per author, **with commit OIDs**) — the field
  that actually carries the approval and its head OID.
- Regression tests assert the query uses `latestOpinionatedReviews` and that
  `approving_review_commits` populates from it when `latestReviews` is empty.
- Live-verified against PR #430: the daemon went from `skip:approval_not_current_head`
  to `enqueue` — the first autonomous-merge path now works.
