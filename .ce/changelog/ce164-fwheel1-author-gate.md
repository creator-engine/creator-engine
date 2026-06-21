## ce-ops#164 / ADR-0010 Phase A on-ramp

- Added the ratified ADR-0010 decision record for moving first-party app-wheel
  parity out of authored PRs.
- Demoted first-party app-wheel parity checks to the `wheel_bake_gate` marker
  and excluded that marker from the author-side offline pytest workflow.
- Added the reusable offline `build_app_wheel_from_source` helper and tests.

CI-only, not install-path-affecting. Runtime dependency floor remains unchanged.
