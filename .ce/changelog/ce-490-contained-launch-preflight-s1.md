## ce-490-contained-launch-preflight-s1

- fix(launch): add pre-spawn policy validation for contained launch - slice 1

  Adds `_validate_contained_launch_plan()` to launch_runtime and wires it into
  the contained-launch path. It fires when `plan.runtime_policy is not None`,
  so bare and host-backend launches are unaffected.

  Three plan-time gaps are checked before any docker/runtime side effect:

  (a) Placeholder image digest (`sha256:000...000`) is a policy-content defect
      verifiable from the record alone; it is always refused with instructions
      to re-run `ce onboard` after runtime_posture resolves
      (`G6-LAUNCH-POLICY-INVALID`, `ContainedLaunchPreflightRefused`).

  (b) Absent bind-mount sources are checked against THIS host's filesystem.
      Optional agent-config dirs (`~/.claude`, `~/.config/claude`, `~/.codex`,
      `~/.config/codex`) are conditionally omitted when absent and emit a
      warning. Any other absent source path, or a sentinel-wrapper path not
      covered by a surviving mount, raises `ContainedLaunchPlanUnverifiable`
      (a `ContainedLaunchPreflightRefused` subclass).

  `launch()` treats (a) as a hard pre-spawn refusal, matching the original
  design. It treats (b) as a *warning* (logged via `LOGGER.warning`,
  non-fatal): the v3 runner backends (`gvisor-proxy`/`docker`) keep their plan
  translation pure/I-O-free by design (see `runner/gvisor_proxy_backend.py`'s
  "translate-vs-execute split") precisely so a runtime-policy-record's
  `mount_manifest` can carry symbolic or not-yet-materialized host paths —
  main's own launch_runtime test corpus relies on this for CI-safe unit tests.
  Hard-refusing (b) unconditionally would regress every such launch, so on an
  unverifiable plan `launch()` warns and falls through to the runtime backend
  with the original (unfiltered) manifest — the same behavior a launch without
  this preflight would have had. `_validate_contained_launch_plan()` itself
  stays fully strict for direct callers (this slice's own dedicated fast unit
  tests in `test_contained_launch_preflight.py` continue to exercise (b) as a
  hard raise), so the check is fully implemented and ready to be tightened
  once `mount_manifest` entries are guaranteed to reference real, resolved
  host paths by the time `launch()` runs.

  Previously, these cases could reach docker, fail at container-creation time,
  or produce an unresolvable launch-probe timeout with no actionable message;
  (a) still fails this way today, (b) now surfaces a named warning instead of
  silence.

  Out of scope for slice 1: the sentinel HUP race / kill-session exited event,
  the zero-digest emitted during onboard, live docker stderr forwarding when
  docker is still reached, and resolving `mount_manifest` entries against real
  host paths so (b) can become a hard refusal without conflicting with
  main's symbolic-plan test fixtures.

  - **Declared work class:** story
