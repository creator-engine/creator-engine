---
slug: ce-s1c-launch-default-policy
date: 2026-07-05
kind: added
scope: runtime/launch
issue: ce-s1c-launch-default-policy
---

**Default controller launch to onboarded runtime policy.**

- `ce onboard --apply` now emits a real default controller
  `runtime-policy-record` beside the legacy runtime posture marker.
- Live `ce launch` resolves the onboarded record by default, validates it, and
  composes the existing visible runtime backend bridge; missing records fail
  closed with onboarding remediation and the explicit `--backend host` opt-out.
- Documented the well-known runtime-policy path and updated launch tests for
  default Docker composition, host opt-out, missing-record refusal, and dry-run
  behavior.
- Review fix: a present-but-corrupt onboarded record (missing/mismatched
  `kind`, or non-mapping content) no longer silently falls through to an
  ungoverned raw launch — it now refuses with a distinct, actionable message
  separate from the absent-record case.
