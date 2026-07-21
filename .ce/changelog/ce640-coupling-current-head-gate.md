# CE640 coupling current-head gate

- Added a versioned, fail-closed current-head coupling-obligation snapshot for
  automerge decision records.
- The actuator now re-fetches the PR's head, base, ref, and changed-path set
  immediately before mutation, refusing missing, indeterminate, or drifted
  evidence.
- The seven observed coupling kinds are represented as deterministic seed
  obligations. This establishes the current-head binding seam while production
  workflow/ruleset arming remains a separately governed rollout step.
- Coupling discovered: an AUTO decision needs an immutable base SHA and an
  obligation snapshot; a mutable base ref is advisory-only and cannot be used
  as pre-mutation coupling evidence.
- The decision workflow now emits its already captured immutable base SHA for
  both pull-request and merge-group subjects, avoiding a token-dependent base
  ref resolution in the decision step while preserving the resolver fallback.
- Press-merge evidence now preserves the live PR base ref when the decision
  payload correctly carries an immutable base SHA.
