---
slug: ce128-dgx-runsc
date: 2026-06-18
kind: added
scope: dgx runsc codex containment
issue: ce-ops#128
---

Added authoring-only DGX runsc/gVisor containerization artifacts for running the
Codex CLI controller under Docker `runsc`: a minimal seat-matched image, a
parameterized runner script for interactive TUI and `codex exec`, and README
apply steps for the DGX Controller.

Follow-up: revised the DGX invocation away from plain Docker bridge/none
networking. The wrapper now defaults to a dedicated `runsc-gvproxy` runtime,
refuses the known-bad plain `runsc`/Docker `--network` path unless explicitly
overridden for diagnostics, and documents HTTPS egress through the DGX
Stage-1 `gvproxy`/`gvisor-tap-vsock` route.
