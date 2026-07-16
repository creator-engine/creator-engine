# Dispatch

Create a governed-seat brief that names the ticket, branch, role, allowed paths
or surfaces, expected evidence, and stop line. Record or verify the work claim
before the target seat starts.

For research dispatches, the controller persists findings in the existing
`.ce/state/research/` notes location, following its naming convention.

## Standing preflight directive (ce-ops#303)

Every implementation dispatch brief must require this order: create a named
exact-path candidate commit first, then run the FULL local validator preflight
only on the clean committed tree. For a validation or review correction, append
a new commit and rerun; never amend, rewrite, or discard the candidate.

Contained seats whose carrier is generated harvest-side run
`ce validate-pr --profile contained-seat`; this is the full suite minus the
harvest-side carrier gate and prints the contained-seat carrier notice.
`--allow-dirty` validates prior committed state and is not candidate evidence;
do not use it in an authoritative handoff instruction. The controller later
generates and commits the carrier, then runs full unprofiled `ce validate-pr`
before attestation or merge-gate handling. Independent review, green checks,
ratification, and merge-gate requirements remain in force. Do not discover
gates via CI. Fast iteration once ce-ops#11 (test-tier split) lands on main:
`pytest -m "not slow"` is iteration only; the validator still gates the push.
