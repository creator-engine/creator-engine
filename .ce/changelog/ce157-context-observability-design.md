---
slug: ce157-context-observability-design
date: 2026-06-22
kind: added
scope: Controller context-window observability design
issue: ce-ops#157
base: 85c9330480a4e80f045f1211a3934d2b01b744f8
---

Adds a small architecture note preserving the Controller context-window
observability requirements for future G-6/G-7 UX design.

- Records the governed-seat problem: project-scoped settings intentionally
  exclude user-level `statusLine` and prompt hooks.
- Captures the required data source, thresholds, boundary-aware nudges, and
  project/CE-native placement constraint.
- Keeps the change design-only: no runtime hooks, vendored status-line scripts,
  product code, or frozen-v1 behavior.
