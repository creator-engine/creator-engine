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

## Test-bearing evidence (required before build evidence counts)

Every brief must explicitly classify the unit as `test-bearing` or
`non-test-bearing`. For a test-bearing unit, the brief must require a structured
RED-to-GREEN record containing all of:

1. exact test node ID(s);
2. the named base or prior head identity;
3. the RED command and captured output against that base/prior head; and
4. the GREEN command and captured output after implementation.

Without the named base/prior-head RED record, a test result is not build proof
and harvest must flag the seal as not ready. The non-test-bearing exemption is
available only when the brief explicitly states a nonempty factual
justification meeting the `no runtime surface` standard above. This local
author-evidence rule does not replace the exact-head CI evidence required
below.

This check is structural detectability, not proof: the parser can flag a
missing or malformed RED/GREEN record, but cannot prove RED output semantically
differs from GREEN. Identical pasted output defeats it. Controllers must weigh
that residual rather than treating a structurally complete record as a proof of
the claimed failure and repair.

## Standing validation directive

Every dispatch brief must carry this line: do not run full local `ce
validate-pr` as a standing pre-push, harvest, controller, or merge-gate
prerequisite. Push the committed current head; wait for required Validate
checks; require independent review and ratification. Evidence names the pushed
head SHA and required Validate run URL/status for that exact head (or required
synthetic merge-group head). Local full-suite transcripts are not gate evidence;
targeted author tests remain optional iteration evidence and cannot substitute
for required CI. `ce validate-pr` remains available as an optional diagnostic.
