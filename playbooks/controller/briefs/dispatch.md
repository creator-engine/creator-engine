# Dispatch

Create a governed-seat brief that names the ticket, branch, role, allowed paths
or surfaces, expected evidence, and stop line. Record or verify the work claim
before the target seat starts.

Every brief must classify the work as either a deployable/integration
capability or `no runtime surface`, and require the worker return to repeat the
classification with evidence. A deployable/integration capability is not
close-ready on merge or green CI alone. Its required closure evidence is:

1. live target or environment, deployed revision or artifact digest,
   observation time, and target exercise command or probe result;
2. governed deployment/IaC reference, or an explicit ratified waiver naming
   the scope, target, revision, and reason no governed deployment/IaC applies;
3. expected observable post-condition, observation source or query, observed
   value and time, and expected-versus-observed reconciliation.

Silence, manual mutation, and unavailable or deferred deployment are not
waivers. Use `no runtime surface` only for pure code, documentation, or
refactoring work with no deployable artifact or configuration and no changed
integration or live runtime behavior; the brief and return must state that
factual basis. Assign evidence collection only within the selected role's
existing authority. Missing live-mutation or waiver authority is a stop line,
not permission to broaden the role. Only the controller decides close-readiness.

For research dispatches, the controller persists findings in the existing
`.ce/state/research/` notes location, following its naming convention.

## Standing preflight directive (ce-ops#303)

Every dispatch brief must carry this line: run the FULL local validator
preflight (`ce validate-pr`, CI-parity) before every self-push or
commit-for-harvest. Contained seats whose carrier is generated harvest-side run
`ce validate-pr --profile contained-seat`; this is the full suite minus the
harvest-side carrier gate and prints the contained-seat carrier notice.
Non-contained seats and harvest/controller runs remain full `ce validate-pr`.
Do not discover gates via CI. Fast iteration once ce-ops#11 (test-tier split)
lands on main: `pytest -m "not slow"` — iteration only, the validator still
gates the push.
