# Dispatch

Create a governed-seat brief that names the ticket, branch, role, allowed paths
or surfaces, expected evidence, and stop line. Record or verify the work claim
before the target seat starts.

## Standing preflight directive (ce-ops#303)

Every dispatch brief must carry this line: run the FULL local validator
preflight (`ce validate-pr`, CI-parity) before every self-push or
commit-for-harvest; contained seats whose carrier is generated harvest-side run
`ce validate-pr --profile contained-seat`, which omits only the carrier-required
gate. Do not discover gates via CI. Fast iteration once ce-ops#11 (test-tier
split) lands on main: `pytest -m "not slow"` — iteration only, the validator
still gates the push.
