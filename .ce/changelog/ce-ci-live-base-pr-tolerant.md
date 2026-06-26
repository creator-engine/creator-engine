---
slug: ce-ci-live-base-pr-tolerant
date: 2026-06-26
kind: fix
scope: ci
---

**make live-comparison base tolerant of behind PRs in pull_request context.**

In the `pull_request` context, the `Resolve live comparison base` step no longer
hard-fails when the PR's recorded base SHA has fallen behind `origin/<base_ref>`.
Instead it fetches the PR's recorded base SHA (falling back to
`origin/<base_ref>` if that SHA is not directly fetchable), emits a `::warning::`,
and continues comparing the PR diff against its own merge-base. This lets
behind-PRs pass their required check and enter the merge queue, which owns
currency-to-HEAD for the actual merge. The `merge_group` context behavior is
unchanged (currency holds by construction there; existing enforcement stays).
