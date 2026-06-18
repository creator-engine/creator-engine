---
slug: ce128-dgx-runsc
date: 2026-06-18
kind: added
scope: dgx runsc codex containment
issue: ce-ops#128
---

Added authoring-only DGX runsc/gVisor containerization artifacts for running the
Codex CLI controller under Docker `--runtime=runsc`: a minimal seat-matched
image, a parameterized runner script for interactive TUI and `codex exec`, and
README apply steps for the DGX Controller.
