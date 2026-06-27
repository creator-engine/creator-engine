# Dispatch

Create a governed-seat brief that names the ticket, branch, role, allowed paths
or surfaces, expected evidence, and stop line. Record or verify the work claim
before the target seat starts.

## Standing preflight directive (ce-ops#303)

Every dispatch brief must carry this line: run the FULL local validator
preflight (`ce validate-pr`, CI-parity) before every self-push or
commit-for-harvest; do not discover gates via CI. The full suite is the bar
before push. Fast iteration once ce-ops#11 (test-tier split) lands on main:
`pytest -m "not slow"` — iteration only, the full suite still gates the push.
