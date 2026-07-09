## ce-502-standby-surface

- fix(standby): provision dedicated main-tracking surface + mint-forge-token repair + drill gate

  Adds deploy/dgx-controller-runsc/provision-standby-surface.sh to provision the standby
  controller with its own main-tracking git worktree (default /home/cedev2/ce-standby-main),
  decoupling it from the shared mutable checkout. Fixes the D6 Drill #1 FAIL where the
  shared checkout on ce-release-0.3.1-rc2 lacked `ce takeover`.

  Adds tools/mint-forge-token.py replacing the traceback-producing helper with a
  guarded implementation that accepts --help and --dry-run without errors.

  Extends continuity_drill_runtime with a standby_liveness gate: drills missing a
  standby liveness proof degrade to WARNING status rather than silently passing.
  The gate only passes with a structured standby-emitted `ce takeover --dry-run
  --json` packet where `ring0_verify.ok=true` and
  `initial_state=AWAITING-OPERATOR`; raw boolean flags remain WARNING.

  - **Declared work class:** S
