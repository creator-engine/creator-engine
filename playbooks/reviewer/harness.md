# Harness

## Runtime Contract

- Reviewer identity must be distinct from author identity.
- A low-context reviewer is refreshed before work: save state, clear context,
  then resume from the review brief.
- Use the GitHub review surface only for review submission.

## Branching Rules

- `base-only-rebase`: run `git range-diff <old>..<new>` and fast-confirm only
  that the branch was rebased or re-pinned.
- `scoped-content-change`: verify only the named findings.
- `full`: perform a normal full code review.

## Halt Conditions

- Missing PR number, old/new refs, or scoped finding list for the selected
  reason.
- Reviewer equals author.
- Dispatch asks for merge or ratification.

## Sunset

Sunset ce-ops#151-specific language when the reviewer dispatch substrate
natively encodes re-review reason and scope.
