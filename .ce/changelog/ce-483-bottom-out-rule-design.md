---
slug: ce-483-bottom-out-rule-design
date: 2026-07-07
kind: story
scope: repair-continuity
issue: ce-ops#483
---

**Recursion bottom-out policy design.**

- Adds the design-only recursion bottom-out policy for autonomous repair incidents.
- Defines hard repair-depth and same-failure thresholds, durable AWAITING-OPERATOR circuit state, watcher behavior, posture/notification surfaces, and the scheduled four-path drill.
- Tightens the design for review: per-signature attempt accumulators resist signature flapping, drill records are isolated from production circuits, durable store and notification contracts are concrete, and different-signature transitions preserve consumed depth.
