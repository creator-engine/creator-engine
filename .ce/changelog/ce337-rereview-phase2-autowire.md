# ce-ops#216 Phase-2 re-review live wiring

- Added same-reviewer approval restoration for the integrator merge path when
  `_classify_head_motion` has already proven base-only drift and GitHub reports
  `REVIEW_REQUIRED`.
- Kept the restore fail-closed for content drift, legacy/unprovable classifier
  states, missing complete review history, and authenticated-reviewer mismatch.
- Added focused unit coverage for base-only restore, content-change refusal, and
  classifier-uncertain refusal.
