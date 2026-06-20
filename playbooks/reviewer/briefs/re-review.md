# Re-review

Branch on `reason`.

- `base-only-rebase`: run `git range-diff <old>..<new>` and approve only if the
  new head is base-only relative to the prior reviewed head.
- `scoped-content-change`: verify only the named prior findings and do not
  re-open unrelated review scope.
- `full`: perform the full-review stage.
