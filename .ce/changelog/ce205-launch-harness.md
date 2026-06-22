---
slug: ce205-launch-harness
ticket: ce-ops#205
type: fix
scope: belt launch-leg e2e harness + sentinel correction
---

Adds an offline, repeatable end-to-end harness for the ce-ops#55 work-pickup
belt's autonomous-launch path and closes the final in-code launch-leg gap it
surfaced.

- New harness `validators/tests/integration/test_belt_launch_e2e.py` drives the
  whole belt launch path — `pickup.launch_lane` ->
  `pco_allocator.allocate_in_place` -> `ce lane launch`
  (`lane_runtime.launch`) — to `LAUNCHED_STATE` in a fully-initialized TEST
  workspace: a real `git init` repo, the `.ce/state` tree, and a brain assertion
  ledger bootstrapped through `brain_runtime.assert_claim` (the SSOT path
  `ce brain assert` drives). It exercises EVERY pre-spawn governance gate offline
  with no tmux server and no network, and drives the full path to a real spawned
  governed lane behind a tmux-availability gate (throwaway session torn down).
- Surfaced + closed the final in-code launch-leg gap: `pickup.LAUNCHED_STATE`
  was the literal `"launched"`, but a fully-governed `ce lane launch --json`
  reports `seat_lifecycle_state: "alive"`
  (`seat_lifecycle.REGISTRATION_STATE_GOVERNED`). The old sentinel never matched
  any real spawn, so the belt reported `launched=False` for EVERY successful
  launch (the seed/dedup confirmation never fired). `LAUNCHED_STATE` is now bound
  to the lifecycle constant.
- `launch_lane` now carries `lane_id` on its spawn-error and non-zero-exit result
  branches (diagnostic fidelity for the controller).
- Updates the stale `test_pickup.py` fake-spawn fixtures from the wrong
  `"launched"` to the runtime-correct `"alive"` sentinel.

Deployment prerequisites (NOT code; documented for the flip): each repo-root must
carry a pre-existing brain assertion ledger at
`<repo-root>/.ce/state/brain/assertions.yaml` (workspace-init), and the cron host
must run a persistent tmux server so the visibility-required `implementer` lane
can spawn an operator-visible pane.
