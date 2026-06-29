---
slug: ce-arma-arming-wiring
date: 2026-06-29
kind: changed
scope: automerge Surface-A arming wiring
issue: ce-armA
---

**Wire dormant-by-default Surface-A automerge arming state into the decide and
actuate workflows.**

- Both automerge workflows now materialize `.ce/state/automerge/policy.json`
  from repository Variables before invoking validator or actuator code.
- `CE_AUTOMERGE_RUN_MODE` arms only when set to exact lowercase `ceo`; unset,
  empty, uppercase, or malformed values materialize `dev` with all class flags
  off. `CE_AUTOMERGE_ENABLING_REF` is carried as the optional enabling decision
  reference. `kill_switch` stays false.
- The decision artifact now carries the actuator-required `repo`, `branch`,
  `base`, `enabling_decision_ref`, and `required_checks` fields so a CEO-mode
  docs AUTO decision has enough metadata to reach the actuator's live-check and
  enable-auto-merge seams.
- Added unit coverage for variable materialization, dormant dev/default
  behavior, workflow wiring, and top-level change-ref actuator acceptance.
