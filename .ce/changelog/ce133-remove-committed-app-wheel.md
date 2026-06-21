## ce-ops#133 / night arc #170 — remove committed first-party app wheel

- Removed the development `validators/wheelhouse/creator_engine_validator-*.whl`
  artifact and its `SHA256SUMS` entry; dependency wheels remain committed and
  hash-checked.
- Replaced committed-wheel parity with a source-built first-party wheel parity
  gate using `build_app_wheel_from_source`.
- Tightened packaging/doctor posture so `validators/wheelhouse/` is dependency
  wheelhouse only, `SHA256SUMS` remains enforced, and `ce doctor --json` exposes
  independent dependency-wheelhouse and committed app-wheel posture.
- Updated clone-mode docs/templates to install dependency wheels before running
  checkout source via `PYTHONPATH=validators`; rehearsal commands use the
  source-mode command prefix, and public served downloads are unchanged.
