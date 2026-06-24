### ce-ops#174 — path-manifest gate resolves live PR base/head, fails closed on stale re-run

- `validate.yml` now anchors checkout to the PR head SHA and resolves the CURRENT PR base/head via `gh api repos/.../pulls/<n>` (injection-safe: full-SHA regex + newline guards) instead of trusting the cached event payload.
- A re-run after rebase→force-push that operates on a stale head now fails closed with a clear message rather than replaying a stale `base..HEAD` payload (the #174 false PASS/FAIL).
