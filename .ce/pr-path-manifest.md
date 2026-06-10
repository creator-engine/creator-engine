# PR path manifest — feat(v3.5-F Q1): per-seat OS-enforced resource bounding (F.0 policy + F.1 systemd-run wrap)

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) requires the declared count and
SHA256 to match the fenced block.

Scope: the Operator-ratified **v3.5-F Q1 fast-track** (mandate
`v35f-Q1-fasttrack-GATE-MANDATE.md`, sha256 `837f3993ebfe74b2…`) — **F.0 + F.1
as ONE PR**: OS-enforced per-seat memory bounding, born-with-the-seat,
policy-driven, provable in `--dry-run`. Out of scope: F.2/F.3/F.4.

- **`schemas/runtime-policy.schema.yaml`** — F.0: `resource_envelopes`
  (`seat`/`fleet`), `resource_enforcement` (`enforce|advisory|off`), and the
  `resource_optout` ratification binding (mirrors `spend_envelopes` /
  `spend_cap_optout`). Additive, optional fields; a record without them stays a
  valid policy.
- **`examples/well-formed/runtime-policy/example-runtime-policy.yml`** — the
  well-formed example now exercises the new fields (desktop host-class values)
  through the existing `ce_runtime_policy` example tests.
- **`validators/creator_engine_validator/resource_bound_spec.py`** *(NEW,
  V1-classified)* — the PURE `ResourceBound` + `build_bounded_command`
  (`systemd-run --user --scope --collect --expand-environment=no --unit … --slice
  ce-fleet.slice -p … -- <governed command>`; `bound=None` → unchanged), the
  fail-closed `parse_resource_policy` fragment reader, the §4.4
  `host_class_defaults` materialization, and the injectable-runner systemd I/O
  edges (support probe, unit-name sanitize/collision resolve, idempotent
  fleet-slice cap, `memory.oom.group` write). `--expand-environment=no` is a
  gate-execution correction OBSERVED live: without it systemd-run expands
  `$`/`${}` tokens inside the wrapped command, mutating Ring-0 output.
- **`validators/creator_engine_validator/launch_runtime.py`** — the `ce launch`
  hook: wrap applied to the OUTPUT of Ring 0 (after the governed command is
  pinned, before `ensure_pane`), `--dry-run` plan gains the `resource_bound`
  block (offline, no probe), enforce/refuse-loudly + ratified opt-down
  (`none (advisory)` stamp), launch-confirm (`memory.oom.group` + fleet cap).
- **`validators/creator_engine_validator/lane_runtime.py`** — the same hook on
  the governed `ce lane launch` path (step 6c after the step-6 Ring-0 build;
  unit keyed by `lane_id`); the `resource_bound` stamp rides the LaunchResult +
  the ignored governance sidecar, never the schema-locked pane record.
- **`validators/creator_engine_validator/ce_cli.py`** — `--runtime-policy` on
  `ce launch`/`ce hud` and `ce lane launch`.
- **`validators/creator_engine_validator/doctor_runtime.py`** — `ce doctor`
  emits the §4.4 host-class default fragment
  (`resource_policy_recommendation`, from MemTotal) for the Operator to ratify
  INTO the policy — bounds are never computed silently at launch.
- **`validators/creator_engine_validator/_versions.py`** — declared delta:
  `V1_RUNTIME += resource_bound_spec` (21 → 22). **V3_RUNTIME +0; registry +0;
  `--list-checks` byte-identical; `version_boundary` ZERO v1↔v3 crossings.**
- **`validators/tests/unit/test_resource_bound_spec.py`** *(NEW)* — pure wrap +
  `None` passthrough + the golden Ring-0-untouched assertion (governed tokens
  byte-identical through the wrap) + fail-closed policy parsing (unratified
  advisory/off refused) + host-class defaults + I/O edges via a fake runner.
- **`validators/tests/unit/fixtures/resource_bound_observed.json`** *(NEW)* —
  the recorded O6/O9/O10 host evidence (crash host, 2026-06-10); the proof
  carrier on runners without user-level cgroup delegation.
- **`validators/tests/unit/test_launch_runtime_resource_bound.py`** *(NEW)* —
  the `ce launch` hook: dry-run renders `resource_bound` offline; refusals fire
  BEFORE any side effect; live wrap + collision suffix + launch-confirm.
- **`validators/tests/unit/test_lane_runtime_resource_bound.py`** *(NEW)* — the
  lane hook: byte-identical governed tail, sidecar stamp, placeholder bounded,
  refusals before pane/registry writes.
- **`validators/tests/integration/test_resource_bound_systemd.py`** *(NEW)* —
  `skipif`-guarded LIVE systemd proof (CI-exercised where the runner supports
  it): wrapped command lands in `ce-fleet.slice/ce-seat-….scope` with limits
  applied (O6/O10), `memory.oom.group` + fleet cap on a live scope, and the
  O9-style isolated kill (64M cap → exit 137, host unaffected).
- **`validators/tests/unit/test_version_boundary.py`** — taxonomy count
  follows the declared delta (`V1_RUNTIME` 21 → 22).
- **`validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl`** +
  **`validators/wheelhouse/SHA256SUMS`** — the shipped app wheel REBUILT from
  this branch's source + the SHA256SUMS re-pin (the #185 lesson: the
  wheel-matches-source CI surface requires the wheel to follow every source
  change; `ce_cli.py` changed here).
- **`.ce/pr-path-manifest.md`** *(this carrier)*.

- **base:** `ea1eea6` (current `main`).
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`,
  Python `sorted()` codepoint order.

AUTHORIZED_PATHS_COUNT=17

AUTHORIZED_PATHS_SHA256=0f0f9e9bd80238c75a4af6e9c32e00220149c5af72b4a052819f157713285162

```text
.ce/pr-path-manifest.md
examples/well-formed/runtime-policy/example-runtime-policy.yml
schemas/runtime-policy.schema.yaml
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/doctor_runtime.py
validators/creator_engine_validator/lane_runtime.py
validators/creator_engine_validator/launch_runtime.py
validators/creator_engine_validator/resource_bound_spec.py
validators/tests/integration/test_resource_bound_systemd.py
validators/tests/unit/fixtures/resource_bound_observed.json
validators/tests/unit/test_lane_runtime_resource_bound.py
validators/tests/unit/test_launch_runtime_resource_bound.py
validators/tests/unit/test_resource_bound_spec.py
validators/tests/unit/test_version_boundary.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl
```
