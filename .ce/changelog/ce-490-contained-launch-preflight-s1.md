## ce-490-contained-launch-preflight-s1

- fix(launch): add pre-spawn policy validation for contained launch - slice 1

  Adds `_validate_contained_launch_plan()` to launch_runtime and wires it into
  the contained-launch path. It fires when `plan.runtime_policy is not None`,
  so bare and host-backend launches are unaffected.

  Three plan-time gaps are now caught before any docker/runtime side effect and
  surface named, actionable pre-spawn refusals (`G6-LAUNCH-POLICY-INVALID`):

  (a) Placeholder image digest (`sha256:000...000`) is detected and refused
      with instructions to re-run `ce onboard` after runtime_posture resolves.

  (b) Absent bind-mount sources are checked. Optional agent-config dirs
      (`~/.claude`, `~/.config/claude`, `~/.codex`, `~/.config/codex`) are
      conditionally omitted when absent and emit a warning. All other absent
      source paths are a hard refusal naming the missing path.

  (c) Sentinel wrapper path coverage is checked: the wrapper must be under at
      least one surviving mount source. If not, launch is refused before docker
      is reached.

  Previously, these cases could reach docker, fail at container-creation time,
  or produce an unresolvable launch-probe timeout with no actionable message.

  Out of scope for slice 1: the sentinel HUP race / kill-session exited event,
  the zero-digest emitted during onboard, and live docker stderr forwarding when
  docker is still reached.

  - **Declared work class:** story
