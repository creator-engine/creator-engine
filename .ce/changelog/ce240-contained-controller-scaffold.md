---
slug: ce240-contained-controller-scaffold
date: 2026-06-26
kind: hardening
scope: deploy/dgx-controller-runsc
issue: ce-ops#240
---

**Contained controller credential seam fail-closed guard.**

- Added a controller `gh` guard stub for the ce-ops#239 transport-deputy seam.
- Routed image-visible `/usr/local/bin/gh` through the guard while preserving the package binary at `/usr/bin/gh`.
- Documented that the unfilled seam refuses gate/source-host credential actions and added offline tests for guard refusal, value-free output, image invariants, and dry-run leakage checks.
