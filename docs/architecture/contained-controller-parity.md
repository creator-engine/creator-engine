# Contained Controller Parity

the contained-controller acceptance work Leg C moves the gate-holding controller into a contained runtime.
C3 is the acceptance side of that move: it defines the behavioral proof that the
contained controller still behaves like the host controller before C4 cutover.

## Design Position

C1, the contained-controller image leg, produces the image and launch path. C3 consumes it only through
a capability adapter. The adapter must expose dispatch, merge-gate, daemon,
operator-attach, credential-injection, and transport-declaration surfaces; it
must not require test code to understand image internals.

C2, the gate credential-injection seam, owns the gate credential injection seam. C3 treats that seam as
mandatory: the contained controller receives a credential handle, neutralizes
ambient `GH_TOKEN` and `GITHUB_TOKEN`, injects the scoped value only into the
child gate environment, and keeps the value out of argv, stdin/input, and logs.

C4 is the cutover gate. It should compare C1 live evidence against the same
capability list captured by
[Contained Controller Parity Acceptance](../operations/CONTAINED_CONTROLLER_PARITY_ACCEPTANCE.md).

## Non-Goals

- No Docker, runsc, socket, or subprocess dependency in C3 unit tests.
- No deploy scaffolding or image/run-script edits in the acceptance lane.
- No new merge authority. The contained controller holds the existing gate; it
  does not bypass review, green checks, head pinning, or the merge queue.

## Architecture Invariants

- Seat dispatch uses herdr/reach and returns an operator-visible terminal
  receipt: terminal kind, attach surface, and pane identity.
- The controller socket remains controller-private and is not leaked into seat
  environments.
- Gate daemons are explicit runtime capabilities, not ambient background
  assumptions. The minimum daemon set is integrator plus review pickup.
- Operator attachment is through the A4 reach plane and visible
  `launch-resume-herdr` surface, never a hidden continuation-only channel.
- The acceptance harness remains offline and injected until C1 supplies a live
  image adapter for the same capability contract.
