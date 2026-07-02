---
slug: ce-367-ce-native-init
date: 2026-07-02
kind: feature
scope: ce-init
issue: ce-ops#367
---

**CE-native ce init project scaffolding.**

- Adds the public CE-native `ce init` project scaffold with embedded offline templates, right-sized work-class artifacts, stage vocabulary, changelog/path-manifest templates, and local CE skills.
- Updates README/docs reconciliation and regenerates the CLI reference for the new surface.
- Refuses `ce init` template writes when a symlink would resolve outside the target project root.
