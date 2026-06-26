# Contained Controller Parity Acceptance

This is the C3 acceptance contract for the contained-controller acceptance work. It defines how the contained
controller must prove parity with the current host controller before C4 cutover.
The proof is capability-level and independent of C1 image internals.

## Scope

C3 accepts a contained controller only when an injected harness can exercise the
capabilities below without depending on Docker, runsc, live subprocesses, or
socket transport. The live C1 image path may later bind these same checks to a
real adapter, but the baseline harness remains offline until that image exists.

Out of scope: image build scripts, deploy scaffolding, runtime registration, and
live DGX containment evidence. Those remain in the C1 lane and the existing
[contained launch proof](./CONTAINED_LAUNCH_PROOF.md).

## Required Parity Capabilities

| Capability | Acceptance requirement |
| --- | --- |
| Seat dispatch | The controller dispatches work through the herdr/reach surface and returns a terminal receipt with kind, surface, and pane identity. The seat environment must not expose a controller socket such as `CONTROLLER_SOCKET` or `CE_CONTROLLER_SOCKET`. |
| Merge gate | The controller may approve and enqueue governed PRs only after approved review, green required checks, and an expected head SHA are present. It must not self-merge, self-review, bypass branch protection, or merge directly from the harness. |
| Gate daemons | The integrator daemon and review-pickup daemon are present, runnable, configurable, and bound to explicit credential handles. Credential values must not be embedded in daemon config. |
| Operator attach | The Operator can attach through the A4 reach plane and the visible `launch-resume-herdr` attach surface. A hidden continuation-only path is not sufficient. |
| Gate credential custody | Gate credentials enter only through the C2/the gate credential-injection seam injection seam. Inherited `GH_TOKEN` and `GITHUB_TOKEN` are neutralized for gate operations, and the injected value must not appear in argv, stdin/input text, or logs. |
| Offline harness | The C3 harness uses injected fakes and performs zero live transport. It does not invoke Docker, runsc, subprocess execution, sockets, or the C1 image. |

## Harness Entry Point

The offline acceptance scaffold lives in
`validators/tests/unit/test_contained_controller_parity.py`.

Run it with:

```bash
PYTHONPATH=validators "${CE_VALIDATOR_PYTHON:-python3}" -m pytest \
  validators/tests/unit/test_contained_controller_parity.py -q
```

The fake controller in that test is intentionally capability-shaped. C1 can
provide a live adapter later by implementing the same observed surfaces:
dispatch receipt, merge-gate decision, daemon inventory, attach surfaces,
credential invocation, and offline/live transport declaration.

## Related Contracts

- [Contained Launch Proof](./CONTAINED_LAUNCH_PROOF.md) owns live containment
  evidence and C1 runtime proof.
- [Integrator Belt Daemon](./INTEGRATOR_BELT_DAEMON.md) defines the controller
  integrator daemon surface.
- [Review Pickup Daemon](./REVIEW_PICKUP_DAEMON.md) defines review routing and
  credential placement expectations.
- [Controller Runtime Contract Protocol](./CONTROLLER_RUNTIME_CONTRACT_PROTOCOL.md)
  anchors controller runtime behavior.
- [Pane Registry Protocol](./PANE_REGISTRY_PROTOCOL.md) anchors visible terminal
  identity for attachable surfaces.

## Cutover Rule

C4 may treat the contained controller as parity-ready only when this offline C3
harness is green and the C1 live adapter supplies equivalent evidence for the
same capabilities. Any missing attach surface, ambient credential use, direct
merge bypass, or hidden controller-seat socket exposure is a cutover blocker.
