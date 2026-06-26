# ce-ops#163 - Foreman Canon Enforced

- Added launch-pinned foreman dispatch contract enforcement so governed seats
  are refused when the required researcher, implementer, and reviewer dispatch
  surfaces are absent or malformed.
- Extended harness seat-contract and seat-class policy validation to require
  the deterministic foreman dispatch role surface.
- Added regression coverage for valid and invalid foreman contracts across
  launch, worker spawn, schemas, examples, and unit validators.
