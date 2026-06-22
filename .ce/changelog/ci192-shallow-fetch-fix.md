---
slug: ci192-shallow-fetch-fix
date: 2026-06-22
kind: fixed
scope: ci validate workflow — shallow-fetch race
issue: ce-ops#192
---

Fixed an intermittent `fatal: shallow file has changed since we read it` failure
in the `Validate` workflow's "Resolve live comparison base" step that ejected
APPROVED + green PRs from the merge queue. The checkout ran with the default
shallow clone (fetch-depth 1), forcing runtime `--depth`/`--unshallow` deepening
that races on `.git/shallow`. Set `fetch-depth: 0` so the comparison-base
`git merge-base` resolves directly with no shallow state and no race.
