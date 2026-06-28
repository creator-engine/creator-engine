# ce-ops: Productize the Governed CE Orchestrator Agent

**Status**: Proposed epic artifact only. Do not file these tickets without
Operator ratification.

Goal: convert the orchestrator controller seat's ad hoc controller behavior into a deterministic,
observable, governed Orchestrator Agent with clear authority boundaries and a
path to CEO-mode composition.

| Order | Ticket | One-line scope | Depends on |
|---|---|---|---|
| 1 | Canonize Orchestrator role contract | Ratify lifecycle, invariants, state machine, inputs/outputs, and non-goals. | Design proposal |
| 2 | Define the controller action-taxonomy (autonomous vs reserved) and ratify it as ADR-0013 | Promote the proposed authority model into the formal substrate-independent authority decision record. | 1 |
| 3 | Add Orchestrator section to controller-bootstrap SSOT | Extend the preview-only SSOT with lifecycle, cadence, decisions, and checkpoint schema pointers. | 1, 2 |
| 4 | Productize dispatch/harvest skill pointers | Create ratified `ce-dispatch` and `ce-harvest` pointers to tracked playbooks and pointer+hash mechanics. | 3 |
| 5 | Specify Orchestrator checkpoint record | Define active objective, workers, claims, blockers, gate state, and next action. | 1 |
| 6 | Specify fleet territory map record | Define read-only claims, branches, PRs, changed paths, locks, and collision checks. | 5 |
| 7 | Specify harvest/fan-in packet | Define durable contained and non-contained worker output packets with diff, evidence, validation, and stop-line result. | 4, 5 |
| 8 | Specify Operator decision queue | Design the HALT/reserved decision surface with options, consequences, authority basis, and resolution records. | 2, 5 |
| 9 | Build read-only Orchestrator cockpit | Render intake, territory, seats, harvest queue, review/gate queue, and Operator decision queue without actuators. | 5, 6, 7, 8 |
| 10 | Wire governed actuation behind action predicates | Add claim, dispatch, harvest, review-route, preflight, PR-update, and merge-gate actions behind the ratified action taxonomy. | 2, 6, 7, 9 |
| 11 | Add Orchestrator evals and trace review | Cover stalled workers, path collisions, missing review, red CI, reserved requests, and conveyor pickup. | 3, 5, 10 |
| 12 | Design CEO-mode / strangeLoop integration | Define cockpit use and independent-review topology without granting privileged authority. | 8, 9, 11 |

Suggested dependency path:

```text
1 -> 2 -> 3 -> 4
1 -> 5 -> 6 -> 7
2 + 5 -> 8
5 + 6 + 7 + 8 -> 9
2 + 6 + 7 + 9 -> 10
3 + 5 + 10 -> 11
8 + 9 + 11 -> 12
```
