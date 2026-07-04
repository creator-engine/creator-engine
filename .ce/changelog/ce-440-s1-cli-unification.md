CLI unification slice 1:

- Renames the v3 public adoption command from `onboard` to `install`.
- Moves the v1 dispatch planner to `ce pickup dispatch-plan`.
- Adds subprocess-only `ce` forwarding shims for the v3 public command groups except `playbook`.
