---
slug: ce-279-surfaces-render
date: 2026-06-26
kind: story
scope: [surfaces/render.py, validators/tests/unit/test_surfaces_render.py]
issue: ce-ops#279
work_class: story
---

- **Declared work class:** story

Added `surfaces/render.py` to render deterministic build arguments and launch
environment exports from `surfaces/manifest.yaml`, with focused unit coverage
for happy paths, null digest handling, host-only warnings, and stable output.
