---
slug: ce217-u3live-herdr-session
date: 2026-06-23
kind: changed
scope: v1 visibility backend / herdr session API
issue: ce-ops#217
---

Wires the U3 live herdr session spawn/write/observe API to the real herdr CLI shape.

- Switches the controller-side herdr socket carrier to `HERDR_SOCKET_PATH`.
- Creates workspaces with `herdr workspace create` using cwd/label/env flags,
  parses the nested `workspace_created` result, and runs the returned root pane
  without the unsupported `pane split --workspace` path.
- Runs pane commands through `herdr pane run <pane_id> <command>` only; cwd/env
  are not sent to `pane run`, and both socket env aliases are refused for
  governed workspace/pane environments.
- Implements ordinary text sends through `herdr pane send-text <pane_id> <text>`,
  while keeping non-UTF-8/control input fail-closed.
- Reads recent pane output through `herdr pane read <pane_id> --source recent
  --lines N --format text|ansi` as stdout text, not JSON.
- Extends mock and live-gated coverage for socket ownership and real CLI command
  shapes.
