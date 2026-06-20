# Reviewer

## What It Does

Defines reviewer actions for full review and re-review. The re-review path
absorbs ce-ops#151 by branching on the reason for review.

## When To Use

Use this playbook when a peer reviewer is dispatched to inspect a PR, validate a
base-only rebase, verify named fixes, or perform a full review after material
changes.

## Preconditions (DoR)

- The reviewer is not the PR author.
- A low-context reviewer is refreshed before dispatch: save state, clear
  context, then resume from the brief.
- The dispatch names `reason`: `base-only-rebase`, `scoped-content-change`, or
  `full`.
- For scoped re-review, the dispatch names the prior findings to verify.

## Outputs (DoD)

- GitHub review submitted as approve, comment, or request changes.
- Evidence includes the inspected range or named findings.
- Re-review does not expand scope unless `reason: full`.
