---
slug: ce195-launch-argv-python-m
ticket: ce-ops#195
type: fix
scope: pickup lane launch argv
---

Makes the pickup belt launch leg PATH-independent.

- Changes `build_lane_argv` to invoke `creator_engine_validator.ce_cli` through
  the active Python interpreter with `python -m`.
- Preserves the existing `lane launch` subcommand and launch flags while
  removing the bare `ce` executable dependency.
- Adds unit coverage for the interpreter/module argv prefix.
