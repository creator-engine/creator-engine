# PR path manifest - ce205-launch-harness

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce205-launch-harness
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Base:
`b3445498` (`origin/main` at branch handoff).

- **Declared work class:** bug

Scope:
ce-ops#205 offline end-to-end belt-launch harness + close the remaining in-code
launch-leg gap. The poll/claim/allocation/lease legs were fixed and merged
(#340/#346/#347); a live canary confirmed claim/allocation/lease and then hit
`ce lane launch` exiting on `G3-BRAIN-BOOTSTRAP-REFUSED`. This PR builds a
deterministic, offline, network-free harness that drives the whole belt launch
path (`pickup.launch_lane` -> `pco_allocator.allocate_in_place` ->
`ce lane launch`) to `LAUNCHED_STATE` in a fully-initialized TEST workspace,
surfacing every remaining governance gate at once.

The harness surfaced the FINAL in-code launch-leg gap: `pickup.LAUNCHED_STATE`
was the literal `"launched"`, but a fully-governed `ce lane launch --json`
reports `seat_lifecycle_state: "alive"`
(`seat_lifecycle.REGISTRATION_STATE_GOVERNED`). The old sentinel NEVER matched,
so the belt would report `launched=False` for EVERY successful spawn (seed/dedup
bookkeeping never confirmed). The sentinel is now bound to the lifecycle
constant. The non-zero-exit / spawn-error result branches now also carry
`lane_id` for diagnostic fidelity.

Per-file purpose:
- **`.ce/changelog/ce205-launch-harness.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce205-launch-harness.md`** *(A)* - this closed path-set carrier.
- **`validators/creator_engine_validator/pickup.py`** *(M)* - bind `LAUNCHED_STATE` to `seat_lifecycle.REGISTRATION_STATE_GOVERNED`; carry `lane_id` on the spawn-error / non-zero-exit `LaunchResult` branches.
- **`validators/tests/integration/test_belt_launch_e2e.py`** *(A)* - offline e2e belt-launch harness: real git repo + `.ce/state` + bootstrapped brain ledger; drives all pre-spawn gates offline and the full path to `LAUNCHED_STATE` behind a real-tmux gate.
- **`validators/tests/unit/test_pickup.py`** *(M)* - update stale fake-spawn sentinels from the wrong `"launched"` to the runtime-correct `"alive"`.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=2697e227c9135a0cedb9e8077fa9f92c03922c19f5637502ef033c4ae739f430

```text
.ce/changelog/ce205-launch-harness.md
.ce/pr-manifests/ce205-launch-harness.md
validators/creator_engine_validator/pickup.py
validators/tests/integration/test_belt_launch_e2e.py
validators/tests/unit/test_pickup.py
```
