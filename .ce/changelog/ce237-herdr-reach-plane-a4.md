---
slug: ce237-herdr-reach-plane-a4
date: 2026-06-26
kind: added
scope: herdr operator reach
issue: ce-ops#237
---

Make the herdr remote attach wrapper expose the Operator reach-plane contract.

- Extends the remote attach plan and CLI JSON with authenticated herdr remote
  reach metadata, runtime isolation separation, and explicit no-host-root /
  no-runtime-attach booleans.
- Carries live contained pane metadata (`pane_id`, `surface_ref`,
  `workspace_id`) without exposing the local herdr socket path.
- Keeps execution limited to `herdr --remote <ssh-target> [--session <name>]`
  and preserves runner-injectable offline tests.
- Documents that reach is herdr-authenticated remote access while isolation is
  independently provided by runsc/Docker/Podman or another runtime.
