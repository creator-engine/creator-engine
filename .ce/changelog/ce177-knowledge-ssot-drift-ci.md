# ce-ops#177 - Knowledge SSOT Drift CI

- Added a tracked authoritative `.ce/brain/assertions.yaml` drift-CI ledger
  containing a semantic assertion for the validate workflow merge-queue trigger.
- Extended brain drift checks with normalized YAML projection assertions so
  workflow/config evidence can anchor to stable semantics rather than raw
  full-file hashes.
- Made `ce brain verify --drift --state-root .ce/state` fall back to the tracked
  `.ce/brain` ledger when local runtime state is absent, keeping clean CI
  checkouts non-vacuous without editing workflow files.
- Added unit and integration coverage for workflow projection drift, acceptable
  workflow variation, and clean-checkout authoritative fallback.
