# Author

## What It Does

Defines author-side PR maintenance actions: base-only refresh and
address-review.

## When To Use

Use this playbook when the author needs to rebase and re-pin a PR without new
ratification, or when the author must address peer review findings.

## Preconditions (DoR)

- The branch belongs to the authoring seat.
- The requested action is either `base-only-refresh` or `address-review`.
- Review findings are available for `address-review`.

## Outputs (DoD)

- Branch is pushed with tests green.
- Base-only refresh carries no material content change beyond rebase, re-pin,
  and validation updates.
- Address-review closeout maps each finding to a fix or explicit non-fix.
