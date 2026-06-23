# ce-ops#148 - Seat Provisioning

- Added `ce bootstrap --repo-root . --venv .venv` for offline source-clone
  provisioning of a controller/seat venv.
- Added target-env doctor coverage that names missing package/script failures
  as `CE-SEAT-ENV` and points remediation at `ce bootstrap`.
- Updated the agent-native bootstrap contract to create a venv, provision it
  from the source checkout, then run installed `ce`/`cev3` scripts.
