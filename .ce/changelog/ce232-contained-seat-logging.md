---
slug: ce232-contained-seat-logging
date: 2026-06-25
kind: fixed
scope: contained-seat persistent logging + runsc run-script cleanups
issue: ce-ops#232
---

**persist contained-seat logs to host.**

- DGX and VPS runsc entrypoints + run-scripts now persist seat logs to a
  host-mounted path so a sandboxed seat's run output survives container teardown.
- Run-script cleanups for the DGX and VPS launchers.
- Extends unit coverage for the DGX/VPS runsc launcher and image paths.
