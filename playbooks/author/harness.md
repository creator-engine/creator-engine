# Harness

## Runtime Contract

- Operate only on the author's own branch.
- For `base-only-refresh`, use the existing ce-base-only-refresh-microauth:
  rebase, re-pin generated artifacts, run validation, and push.
- For `address-review`, change only what is necessary to satisfy actionable
  review findings.

## Halt Conditions

- Branch ownership is unclear.
- Base-only refresh would require material content edits.
- Review finding needs new ratification or a widened scope.

## Sunset

Sunset the explicit base-only microauth branch when the controller dispatch
surface carries base-refresh authority as first-class machine-readable data.
