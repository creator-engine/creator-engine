---
slug: ce217-u3live-herdr-session
date: 2026-06-23
kind: changed
scope: v1 visibility backend / herdr session API
issue: ce-ops#217
---

Wires the U3 live herdr session write/observe API to the real herdr CLI shape.

- Switches the controller-side herdr socket carrier to `HERDR_SOCKET_PATH`.
- Implements ordinary text sends through `herdr pane send-text <pane_id> <text>`,
  while keeping non-UTF-8/control input fail-closed.
- Reads recent pane output through `herdr pane read <pane_id> --source recent
  --lines N --format text|ansi` as stdout text, not JSON.
- Extends mock and live-gated coverage for socket ownership and real CLI command
  shapes.
