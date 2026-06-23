---
slug: ce217-u3-herdr-backend
date: 2026-06-23
kind: added
scope: v1 visibility backend / herdr integration seam
issue: ce-ops#217
---

Adds the live `terminal_kind=herdr` visibility backend for Cockpit-on-herdr U3.

- Wires `HerdrSession` to drive herdr as a separate subprocess/socket client:
  workspace create, pane split/run/read, and wait agent-status. The U4 steer
  path (`send`) remains fail-closed until attribution lands.
- Registers `HerdrVisibilityBackend` as the live `operator_inspectable` surface
  and preserves the Pane Registry `terminal.kind` / `visibility` /
  `surface_ref` contract.
- Retires the #368 `pty.fork` byte-tap path: `terminal_kind=headless` is no
  longer registered as a live backend, and `spawn_pty_session()` fails closed.
- Extends Pane Registry and seat-lifecycle schemas/checks for `terminal.kind:
  herdr`, with `surface_ref`, `pane_id`, and `pid`.
- Keeps the U2 pure containment planner as the source of the §7 socket ownership
  invariant: the herdr control socket remains substrate/controller-owned and is
  never passed to the governed seat.
